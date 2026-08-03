import {
  DEFAULT_ANALYSIS_REQUEST_STATE,
  DEFAULT_COMPARISON_REQUEST_STATE,
  analysisRequestStateSchema,
  applyComparisonPeriodPreset,
  buildAnalysisRequest,
  buildComparisonRequest,
  comparisonRequestStateSchema,
  createDefaultComparisonRequestState
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
  it("keeps the default comparison typed with adjacent, non-empty filters", () => {
    const request = buildComparisonRequest(DEFAULT_COMPARISON_REQUEST_STATE);

    expect(request).toMatchObject({
      baseline_label: "Önceki 1 saat",
      comparison_label: "Son 1 saat",
      metrics: ["event_count", "error_rate", "p95_duration_ms"],
      group_by: ["service", "severity"],
      top_n: 10
    });
    expect(request.baseline_filter?.end_time).toBe(request.comparison_filter?.start_time);
    expect(request.baseline_filter).toHaveProperty("start_time");
    expect(request.comparison_filter).toHaveProperty("end_time");
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

  it("requires all four period boundaries to prevent identical empty snapshots", () => {
    expect(() =>
      comparisonRequestStateSchema.parse({
        ...DEFAULT_COMPARISON_REQUEST_STATE,
        baselineStartTime: "",
        baselineEndTime: "",
        comparisonStartTime: "",
        comparisonEndTime: ""
      })
    ).toThrow();
  });

  it("creates adjacent, equal UTC windows from a deterministic preset", () => {
    const now = new Date("2026-08-03T12:00:00.000Z");
    const originalBaselineStart = DEFAULT_COMPARISON_REQUEST_STATE.baselineStartTime;
    const state = applyComparisonPeriodPreset(DEFAULT_COMPARISON_REQUEST_STATE, "last_hour", now);
    const request = buildComparisonRequest(state);

    expect(request).toMatchObject({
      baseline_label: "Önceki 1 saat",
      comparison_label: "Son 1 saat",
      baseline_filter: {
        start_time: "2026-08-03T10:00:00.000Z",
        end_time: "2026-08-03T11:00:00.000Z"
      },
      comparison_filter: {
        start_time: "2026-08-03T11:00:00.000Z",
        end_time: "2026-08-03T12:00:00.000Z"
      }
    });
    expect(DEFAULT_COMPARISON_REQUEST_STATE.baselineStartTime).toBe(originalBaselineStart);
  });

  it("creates a useful last-hour default without sharing mutable state", () => {
    const now = new Date("2026-08-03T12:00:00.000Z");
    const first = createDefaultComparisonRequestState(now);
    const second = createDefaultComparisonRequestState(now);

    expect(first).toEqual(second);
    expect(first).not.toBe(second);
    expect(first.metrics).not.toBe(second.metrics);
    expect(first.groupBy).not.toBe(second.groupBy);
    expect(first.comparisonStartTime).toBe(first.baselineEndTime);
  });

  it("rejects invalid preset clocks and more than four group dimensions", () => {
    expect(() =>
      applyComparisonPeriodPreset(
        DEFAULT_COMPARISON_REQUEST_STATE,
        "last_24_hours",
        new Date(Number.NaN)
      )
    ).toThrow("Preset zamanı geçerli olmalıdır");

    expect(() =>
      comparisonRequestStateSchema.parse({
        ...DEFAULT_COMPARISON_REQUEST_STATE,
        groupBy: ["endpoint", "event_type", "host", "http_status", "service"]
      })
    ).toThrow();
  });
});
