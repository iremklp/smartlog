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
    const fetchMock = installFetchResponse({
      events: [],
      page: { offset: 10, limit: 25, returned: 0, total: 0 },
      facets: {},
      aggregation: null,
      query_duration_ms: 0.5,
      snapshot_size: 0,
      index_used: false,
      candidate_count: 0,
      warnings: []
    });
    const query: EventQuery = {
      filter: { severities: ["error"] },
      offset: 10,
      limit: 25
    };

    await queryEvents(query);

    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toBe("http://localhost:8000/query");
    expect(JSON.parse(String(init?.body))).toEqual({
      query: {
        ...query,
        include_events: true,
        include_total: true,
        include_facets: false,
        filter: {
          ...query.filter,
          message_case_sensitive: false
        }
      }
    });
  });

  it("posts analysis payloads directly to the versioned endpoint", async () => {
    const fetchMock = installFetchResponse({
      analysis_id: "analysis-1",
      generated_at: "2026-08-05T10:00:00Z",
      input_event_count: 1,
      matched_event_count: 1,
      analysis_duration_ms: 1,
      summary: null,
      timeline: null,
      distributions: [],
      latency: null,
      http: null,
      insights: [],
      samples: [],
      warnings: []
    });
    const payload = {
      include_summary: true,
      include_samples: false,
      top_n: 5
    };

    await analyzeEvents(payload);

    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toBe("http://localhost:8000/api/v1/analysis");
    expect(JSON.parse(String(init?.body))).toEqual({
      ...payload,
      include_timeline: true,
      include_distributions: true,
      include_latency: true,
      include_http: true,
      include_insights: true,
      sample_size: 10,
      group_fields: ["severity", "source_type", "event_type", "parser_name", "service", "host"],
      percentiles: [50, 75, 90, 95, 99]
    });
  });

  it("posts comparison payloads directly to the versioned endpoint", async () => {
    const fetchMock = installFetchResponse({
      baseline_label: "Before",
      comparison_label: "After",
      baseline_summary: {
        input_event_count: 0,
        matched_event_count: 0,
        trace_count: 0,
        debug_count: 0,
        info_count: 0,
        warning_count: 0,
        error_count: 0,
        critical_count: 0,
        unknown_count: 0,
        error_or_critical_count: 0,
        error_rate: 0,
        critical_rate: 0,
        unique_event_type_count: 0,
        unique_service_count: 0,
        unique_host_count: 0,
        unique_parser_count: 0,
        unique_source_type_count: 0,
        earliest_timestamp: null,
        latest_timestamp: null,
        time_span_seconds: null,
        events_per_second: null,
        events_per_minute: null,
        events_with_duration: 0,
        events_with_http_status: 0,
        duplicate_content_count: 0,
        out_of_order_timestamp_count: 0
      },
      comparison_summary: {
        input_event_count: 0,
        matched_event_count: 0,
        trace_count: 0,
        debug_count: 0,
        info_count: 0,
        warning_count: 0,
        error_count: 0,
        critical_count: 0,
        unknown_count: 0,
        error_or_critical_count: 0,
        error_rate: 0,
        critical_rate: 0,
        unique_event_type_count: 0,
        unique_service_count: 0,
        unique_host_count: 0,
        unique_parser_count: 0,
        unique_source_type_count: 0,
        earliest_timestamp: null,
        latest_timestamp: null,
        time_span_seconds: null,
        events_per_second: null,
        events_per_minute: null,
        events_with_duration: 0,
        events_with_http_status: 0,
        duplicate_content_count: 0,
        out_of_order_timestamp_count: 0
      },
      baseline_event_count: 0,
      comparison_event_count: 0,
      duration_ms: 1,
      metric_comparisons: [],
      group_comparisons: [],
      insights: [],
      warnings: []
    });
    const payload: ComparisonRequest = {
      baseline_label: "Before",
      comparison_label: "After",
      metrics: ["event_count"]
    };

    await compareEvents(payload);

    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toBe("http://localhost:8000/api/v1/analysis/compare");
    expect(JSON.parse(String(init?.body))).toEqual({
      ...payload,
      group_by: ["severity", "event_type", "service"],
      top_n: 10,
      minimum_group_count: 1,
      include_new_groups: true,
      include_disappeared_groups: true,
      normalize_by_time_span: true
    });
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

  it("rejects query responses that drift from pagination contract", async () => {
    installFetchResponse({
      events: [],
      page: { offset: 0, limit: 10, has_next: true, total: 100 },
      query_duration_ms: 1,
      snapshot_size: 100,
      index_used: true,
      candidate_count: 10
    });

    await expect(queryEvents({ offset: 0, limit: 10 })).rejects.toThrow(
      /Contract validation failed for \/query/
    );
  });

  it("rejects analysis responses that drift from required field names", async () => {
    installFetchResponse({
      generated_at: "2026-08-05T10:00:00Z",
      input_event_count: 1,
      matched_event_count: 1,
      analysis_duration_ms: 1,
      summary: null,
      distributions: [],
      insights: [],
      samples: [],
      warnings: []
    });

    await expect(analyzeEvents({})).rejects.toThrow(
      /Contract validation failed for \/api\/v1\/analysis/
    );
  });
});
