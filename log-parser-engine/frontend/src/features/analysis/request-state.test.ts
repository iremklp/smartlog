import {
  DEFAULT_ANALYSIS_REQUEST_STATE,
  DEFAULT_COMPARISON_REQUEST_STATE,
  analysisRequestStateSchema,
  buildAnalysisRequest,
  buildComparisonRequest,
  comparisonRequestStateSchema
} from "./request-state";

describe("analysis request state", () => {
  it("builds a bounded backend request from the deterministic defaults", () => {
    const request = buildAnalysisRequest(DEFAULT_ANALYSIS_REQUEST_STATE);

    expect(request).toMatchObject({
      top_n: 10,
      group_fields: ["severity", "service", "event_type"],
      include_summary: true,
      include_timeline: true,
      include_distributions: true,
      include_latency: false,
      include_http: false,
      include_insights: false,
      include_samples: false
    });
    expect(request).not.toHaveProperty("start_time");
    expect(request).not.toHaveProperty("end_time");
    expect(request).not.toHaveProperty("time_bucket_seconds");
  });

  it("sends an explicit UTC bucket only after the user selects one", () => {
    const request = buildAnalysisRequest({
      ...DEFAULT_ANALYSIS_REQUEST_STATE,
      timeBucketSeconds: 300
    });

    expect(request.time_bucket_seconds).toBe(300);
  });

  it("converts datetime-local values to timezone-aware UTC wire values", () => {
    const startTime = "2026-07-25T10:00";
    const endTime = "2026-07-25T11:00";

    const request = buildAnalysisRequest({
      ...DEFAULT_ANALYSIS_REQUEST_STATE,
      startTime,
      endTime
    });

    expect(request.start_time).toBe(new Date(startTime).toISOString());
    expect(request.end_time).toBe(new Date(endTime).toISOString());
  });

  it("rejects reversed time bounds and UI values above the rendering limits", () => {
    expect(() =>
      analysisRequestStateSchema.parse({
        ...DEFAULT_ANALYSIS_REQUEST_STATE,
        startTime: "2026-07-25T11:00",
        endTime: "2026-07-25T10:00"
      })
    ).toThrow();

    expect(() =>
      analysisRequestStateSchema.parse({
        ...DEFAULT_ANALYSIS_REQUEST_STATE,
        topN: 21
      })
    ).toThrow();

    expect(() =>
      analysisRequestStateSchema.parse({
        ...DEFAULT_ANALYSIS_REQUEST_STATE,
        groupFields: []
      })
    ).toThrow();
  });
});

describe("comparison request state", () => {
  it("keeps comparison request state typed without emitting empty filters", () => {
    const request = buildComparisonRequest(DEFAULT_COMPARISON_REQUEST_STATE);

    expect(request).toMatchObject({
      baseline_label: "Önceki dönem",
      comparison_label: "Karşılaştırma dönemi",
      metrics: ["event_count", "error_rate", "p95_duration_ms"],
      group_by: ["service", "severity"],
      top_n: 10
    });
    expect(request).not.toHaveProperty("baseline_filter");
    expect(request).not.toHaveProperty("comparison_filter");
  });

  it("requires at least one metric or comparison group", () => {
    expect(() =>
      comparisonRequestStateSchema.parse({
        ...DEFAULT_COMPARISON_REQUEST_STATE,
        metrics: [],
        groupBy: []
      })
    ).toThrow();
  });
});
