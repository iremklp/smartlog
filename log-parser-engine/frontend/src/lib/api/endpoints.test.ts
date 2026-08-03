import { analyzeEvents, compareEvents, getHealth, parseWithParser, queryEvents } from "./endpoints";
import type { ComparisonRequest, EventQuery } from "./types";

function installFetchResponse(
  payload: unknown,
  status = 200
): ReturnType<typeof vi.fn<typeof fetch>> {
  const fetchMock = vi.fn<typeof fetch>();
  fetchMock.mockResolvedValue(
    new Response(JSON.stringify(payload), {
      status,
      headers: { "Content-Type": "application/json" }
    })
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("API endpoints", () => {
  it("puts parser identity only in the parse path", async () => {
    const fetchMock = installFetchResponse({});
    const payload = {
      raw_log: '{"level":"error"}',
      allow_disabled_parser: false
    };

    await parseWithParser("json/parser", payload);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toBe("http://localhost:8000/parse/json%2Fparser");
    expect(init?.method).toBe("POST");
    expect(JSON.parse(String(init?.body))).toEqual(payload);
    expect(JSON.parse(String(init?.body))).not.toHaveProperty("parser_name");
  });

  it("wraps event queries in the backend query envelope", async () => {
    const fetchMock = installFetchResponse({});
    const query: EventQuery = {
      filter: { severities: ["error"] },
      offset: 10,
      limit: 25
    };

    await queryEvents(query);

    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toBe("http://localhost:8000/query");
    expect(JSON.parse(String(init?.body))).toEqual({ query });
  });

  it("posts analysis payloads directly to the versioned endpoint", async () => {
    const fetchMock = installFetchResponse({});
    const payload = {
      include_summary: true,
      include_samples: false,
      top_n: 5
    };

    await analyzeEvents(payload);

    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toBe("http://localhost:8000/api/v1/analysis");
    expect(JSON.parse(String(init?.body))).toEqual(payload);
  });

  it("posts comparison payloads directly to the versioned endpoint", async () => {
    const fetchMock = installFetchResponse({});
    const payload: ComparisonRequest = {
      baseline_label: "Before",
      comparison_label: "After",
      metrics: ["event_count"]
    };

    await compareEvents(payload);

    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toBe("http://localhost:8000/api/v1/analysis/compare");
    expect(JSON.parse(String(init?.body))).toEqual(payload);
  });

  it("extracts a safe message from structured API error details", async () => {
    installFetchResponse(
      {
        detail: {
          code: "SERVICE_UNAVAILABLE",
          message: "The service is temporarily unavailable."
        }
      },
      503
    );

    await expect(getHealth()).rejects.toMatchObject({
      name: "ApiError",
      status: 503,
      message: "The service is temporarily unavailable.",
      detail: "The service is temporarily unavailable."
    });
  });
});
