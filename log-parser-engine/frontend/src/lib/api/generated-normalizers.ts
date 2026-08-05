import type {
  AnalysisRequest,
  EventAggregationRequest,
  ComparisonRequest,
  EventFilter,
  EventQuery
} from "./types";
import type {
  AnalysisRequest as GeneratedAnalysisRequest,
  ComparisonRequest as GeneratedComparisonRequest,
  EventQuery as GeneratedEventQuery
} from "./generated-contracts";

type GeneratedEventFilter = NonNullable<GeneratedEventQuery["filter"]>;

function normalizeEventFilter(filter: EventFilter): GeneratedEventFilter {
  return {
    ...filter,
    message_case_sensitive: filter.message_case_sensitive ?? false
  };
}

function normalizeAggregation(
  aggregation: EventAggregationRequest | null | undefined
): GeneratedEventQuery["aggregation"] {
  if (!aggregation) {
    return aggregation;
  }
  return {
    ...aggregation,
    limit: aggregation.limit ?? 100
  };
}

export function normalizeEventQuery(input: EventQuery): GeneratedEventQuery {
  const normalizedFilter = input.filter ? normalizeEventFilter(input.filter) : undefined;
  const { include_null_facet: _ignoredIncludeNullFacet, ...rest } = input;

  return {
    ...rest,
    filter: normalizedFilter,
    aggregation: normalizeAggregation(input.aggregation),
    offset: input.offset ?? 0,
    include_events: input.include_events ?? true,
    include_total: input.include_total ?? true,
    include_facets: input.include_facets ?? false
  };
}

export function normalizeAnalysisRequest(input: AnalysisRequest): GeneratedAnalysisRequest {
  return {
    ...input,
    filter: input.filter ? normalizeEventFilter(input.filter) : input.filter,
    include_summary: input.include_summary ?? true,
    include_timeline: input.include_timeline ?? true,
    include_distributions: input.include_distributions ?? true,
    include_latency: input.include_latency ?? true,
    include_http: input.include_http ?? true,
    include_insights: input.include_insights ?? true,
    include_samples: input.include_samples ?? false,
    sample_size: input.sample_size ?? 10,
    group_fields: input.group_fields ?? [
      "severity",
      "source_type",
      "event_type",
      "parser_name",
      "service",
      "host"
    ],
    percentiles: input.percentiles ?? [50, 75, 90, 95, 99]
  };
}

export function normalizeComparisonRequest(
  input: ComparisonRequest
): GeneratedComparisonRequest {
  return {
    ...input,
    baseline_label: input.baseline_label ?? "Baseline",
    comparison_label: input.comparison_label ?? "Comparison",
    metrics: input.metrics ?? ["event_count", "error_rate", "p95_duration_ms"],
    group_by: input.group_by ?? ["severity", "event_type", "service"],
    top_n: input.top_n ?? 10,
    minimum_group_count: input.minimum_group_count ?? 1,
    include_new_groups: input.include_new_groups ?? true,
    include_disappeared_groups: input.include_disappeared_groups ?? true,
    normalize_by_time_span: input.normalize_by_time_span ?? true,
    baseline_filter: input.baseline_filter
      ? normalizeEventFilter(input.baseline_filter)
      : input.baseline_filter,
    comparison_filter: input.comparison_filter
      ? normalizeEventFilter(input.comparison_filter)
      : input.comparison_filter
  };
}
