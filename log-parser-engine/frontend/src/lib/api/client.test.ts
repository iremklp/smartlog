import { ApiError, requestJson } from "./client";

function installResponse(response: Response): void {
  vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockResolvedValue(response));
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("API client errors", () => {
  it("preserves the safe analysis error envelope and retry guidance", async () => {
    installResponse(
      new Response(
        JSON.stringify({
          detail: "Analysis capacity is temporarily exhausted.",
          error: {
            code: "ANALYSIS_CONCURRENCY_LIMIT_REACHED",
            message: "Analysis capacity is temporarily exhausted.",
            request_id: "request-123",
            timestamp: "2026-08-03T12:00:00Z",
            details: { limit: 1, fields: ["group_fields"] }
          }
        }),
        {
          status: 429,
          headers: {
            "Content-Type": "application/json",
            "Retry-After": "1"
          }
        }
      )
    );

    await expect(requestJson("/api/v1/analysis", { method: "POST" })).rejects.toMatchObject({
      name: "ApiError",
      status: 429,
      message: "Analysis capacity is temporarily exhausted.",
      detail: "Analysis capacity is temporarily exhausted.",
      code: "ANALYSIS_CONCURRENCY_LIMIT_REACHED",
      requestId: "request-123",
      details: { limit: 1, fields: ["group_fields"] },
      retryAfter: "1"
    });
  });

  it("also reads structured metadata from an object detail envelope", async () => {
    installResponse(
      new Response(
        JSON.stringify({
          detail: {
            code: "SERVICE_UNAVAILABLE",
            message: "The service is temporarily unavailable.",
            request_id: "request-456",
            details: { component: "analysis" }
          }
        }),
        { status: 503, headers: { "Content-Type": "application/json" } }
      )
    );

    await expect(requestJson("/health")).rejects.toMatchObject({
      code: "SERVICE_UNAVAILABLE",
      requestId: "request-456",
      details: { component: "analysis" }
    });
  });

  it("ignores malformed structured metadata without losing the safe message", async () => {
    installResponse(
      new Response(
        JSON.stringify({
          detail: "Request rejected.",
          error: {
            code: 42,
            request_id: ["not", "a", "request id"],
            details: ["not", "an", "object"]
          }
        }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      )
    );

    let caught: unknown;
    try {
      await requestJson("/api/v1/analysis");
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(ApiError);
    expect(caught).toMatchObject({ status: 400, message: "Request rejected." });
    expect((caught as ApiError).code).toBeUndefined();
    expect((caught as ApiError).requestId).toBeUndefined();
    expect((caught as ApiError).details).toBeUndefined();
  });

  it("tolerates non-JSON failures while preserving Retry-After", async () => {
    installResponse(
      new Response("upstream unavailable", {
        status: 503,
        headers: { "Content-Type": "text/plain", "Retry-After": "120" }
      })
    );

    await expect(requestJson("/health")).rejects.toMatchObject({
      name: "ApiError",
      status: 503,
      message: "Request failed with status 503",
      retryAfter: "120"
    });
  });
});
