import type {
  AnalysisRequest,
  AnalysisResponse,
  AnalysisSummary,
  ComparisonRequest,
  ComparisonResponse
} from "./types";

const emptySummary: AnalysisSummary = {
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
};

describe("statistical analysis API contracts", () => {
  it("uses backend-supported literal dimensions and metrics in requests", () => {
    const analysis: AnalysisRequest = {
      group_fields: ["severity", "endpoint", "status_class"]
    };
    const comparison: ComparisonRequest = {
      metrics: ["event_count", "p95_duration_ms", "throughput"],
      group_by: ["service", "http_status"]
    };

    expect(analysis.group_fields).toEqual(["severity", "endpoint", "status_class"]);
    expect(comparison.metrics).toEqual(["event_count", "p95_duration_ms", "throughput"]);
  });

  it("models analysis response modules with concrete nested contracts", () => {
    const response: AnalysisResponse = {
      analysis_id: "73d64de4-04a2-45cb-8d6c-530f6332dd77",
      generated_at: "2026-08-03T12:00:00Z",
      input_event_count: 0,
      matched_event_count: 0,
      analysis_duration_ms: 1.5,
      summary: emptySummary,
      timeline: null,
      distributions: [],
      latency: null,
      http: null,
      insights: [],
      samples: [],
      warnings: []
    };

    expect(response.summary?.error_or_critical_count).toBe(0);
  });

  it("models comparison metrics, groups, and interpretations explicitly", () => {
    const response: ComparisonResponse = {
      baseline_label: "Before",
      comparison_label: "After",
      baseline_summary: emptySummary,
      comparison_summary: emptySummary,
      baseline_event_count: 0,
      comparison_event_count: 0,
      duration_ms: 2,
      metric_comparisons: [
        {
          metric: "event_count",
          unit: "count",
          baseline_value: 0,
          comparison_value: 0,
          absolute_change: 0,
          percent_change: 0,
          direction: "unchanged",
          significant: false,
          interpretation: "neutral",
          notes: []
        }
      ],
      group_comparisons: [],
      insights: [],
      warnings: []
    };

    expect(response.metric_comparisons[0]?.interpretation).toBe("neutral");
  });
});
