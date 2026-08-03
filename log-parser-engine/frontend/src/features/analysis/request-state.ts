import { z } from "zod";

import type {
  AnalysisGroupField,
  AnalysisRequest,
  ComparisonGroup,
  ComparisonMetric,
  ComparisonRequest,
  EventFilter
} from "../../lib/api/types";

export const ANALYSIS_GROUP_OPTIONS = [
  { value: "severity", label: "Severity" },
  { value: "service", label: "Service" },
  { value: "event_type", label: "Event type" },
  { value: "source_type", label: "Source type" },
  { value: "parser_name", label: "Parser" },
  { value: "host", label: "Host" },
  { value: "endpoint", label: "Endpoint" },
  { value: "status_class", label: "HTTP status class" }
] as const satisfies ReadonlyArray<{ value: AnalysisGroupField; label: string }>;

const analysisGroupValues = ANALYSIS_GROUP_OPTIONS.map((option) => option.value) as [
  AnalysisGroupField,
  ...AnalysisGroupField[]
];

const optionalLocalDateTime = z.string().trim();

export const analysisRequestStateSchema = z
  .object({
    startTime: optionalLocalDateTime,
    endTime: optionalLocalDateTime,
    timeBucketSeconds: z.union([z.literal("auto"), z.coerce.number().int().min(60).max(86_400)]),
    topN: z.coerce.number().int().min(1).max(20),
    groupFields: z.array(z.enum(analysisGroupValues)).min(1).max(4)
  })
  .superRefine((value, context) => {
    validateTimeRange(value.startTime, value.endTime, context);
  });

export type AnalysisRequestState = z.infer<typeof analysisRequestStateSchema>;

export const DEFAULT_ANALYSIS_REQUEST_STATE: AnalysisRequestState = {
  startTime: "",
  endTime: "",
  timeBucketSeconds: "auto",
  topN: 10,
  groupFields: ["severity", "service", "event_type"]
};

const comparisonMetricValues = [
  "event_count",
  "error_rate",
  "critical_rate",
  "average_duration_ms",
  "p50_duration_ms",
  "p95_duration_ms",
  "p99_duration_ms",
  "server_error_rate",
  "client_error_rate",
  "throughput"
] as const satisfies readonly ComparisonMetric[];

const comparisonGroupValues = [
  "endpoint",
  "event_type",
  "host",
  "http_status",
  "parser_name",
  "service",
  "severity"
] as const satisfies readonly ComparisonGroup[];

export const comparisonRequestStateSchema = z
  .object({
    baselineLabel: z.string().trim().min(1).max(100),
    comparisonLabel: z.string().trim().min(1).max(100),
    baselineStartTime: optionalLocalDateTime,
    baselineEndTime: optionalLocalDateTime,
    comparisonStartTime: optionalLocalDateTime,
    comparisonEndTime: optionalLocalDateTime,
    metrics: z.array(z.enum(comparisonMetricValues)).max(10),
    groupBy: z.array(z.enum(comparisonGroupValues)).max(9),
    topN: z.coerce.number().int().min(1).max(20)
  })
  .superRefine((value, context) => {
    validateTimeRange(value.baselineStartTime, value.baselineEndTime, context, "baseline");
    validateTimeRange(value.comparisonStartTime, value.comparisonEndTime, context, "comparison");
    if (value.metrics.length === 0 && value.groupBy.length === 0) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["metrics"],
        message: "En az bir metrik veya grup seçilmelidir"
      });
    }
  });

export type ComparisonRequestState = z.infer<typeof comparisonRequestStateSchema>;

export const DEFAULT_COMPARISON_REQUEST_STATE: ComparisonRequestState = {
  baselineLabel: "Önceki dönem",
  comparisonLabel: "Karşılaştırma dönemi",
  baselineStartTime: "",
  baselineEndTime: "",
  comparisonStartTime: "",
  comparisonEndTime: "",
  metrics: ["event_count", "error_rate", "p95_duration_ms"],
  groupBy: ["service", "severity"],
  topN: 10
};

export function buildAnalysisRequest(input: AnalysisRequestState): AnalysisRequest {
  const value = analysisRequestStateSchema.parse(input);
  const startTime = toUtcIso(value.startTime);
  const endTime = toUtcIso(value.endTime);
  return {
    ...(startTime ? { start_time: startTime } : {}),
    ...(endTime ? { end_time: endTime } : {}),
    ...(typeof value.timeBucketSeconds === "number"
      ? { time_bucket_seconds: value.timeBucketSeconds }
      : {}),
    top_n: value.topN,
    group_fields: value.groupFields,
    percentiles: [50, 95, 99],
    include_summary: true,
    include_timeline: true,
    include_distributions: true,
    include_latency: false,
    include_http: false,
    include_insights: false,
    include_samples: false
  };
}

export function buildComparisonRequest(input: ComparisonRequestState): ComparisonRequest {
  const value = comparisonRequestStateSchema.parse(input);
  const baselineFilter = buildTimeFilter(value.baselineStartTime, value.baselineEndTime);
  const comparisonFilter = buildTimeFilter(value.comparisonStartTime, value.comparisonEndTime);
  return {
    baseline_label: value.baselineLabel,
    comparison_label: value.comparisonLabel,
    ...(baselineFilter ? { baseline_filter: baselineFilter } : {}),
    ...(comparisonFilter ? { comparison_filter: comparisonFilter } : {}),
    metrics: value.metrics,
    group_by: value.groupBy,
    top_n: value.topN,
    minimum_group_count: 1,
    include_new_groups: true,
    include_disappeared_groups: true,
    normalize_by_time_span: true
  };
}

function buildTimeFilter(start: string, end: string): EventFilter | undefined {
  const startTime = toUtcIso(start);
  const endTime = toUtcIso(end);
  if (!startTime && !endTime) {
    return undefined;
  }
  return {
    ...(startTime ? { start_time: startTime } : {}),
    ...(endTime ? { end_time: endTime } : {})
  };
}

function toUtcIso(value: string): string | undefined {
  if (!value) {
    return undefined;
  }
  return new Date(value).toISOString();
}

function validateTimeRange(
  start: string,
  end: string,
  context: z.RefinementCtx,
  pathPrefix?: string
): void {
  const startDate = parseLocalDateTime(start);
  const endDate = parseLocalDateTime(end);
  if (start && startDate === null) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: [pathPrefix ? `${pathPrefix}StartTime` : "startTime"],
      message: "Geçerli bir başlangıç zamanı girin"
    });
  }
  if (end && endDate === null) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: [pathPrefix ? `${pathPrefix}EndTime` : "endTime"],
      message: "Geçerli bir bitiş zamanı girin"
    });
  }
  if (startDate && endDate && startDate >= endDate) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: [pathPrefix ? `${pathPrefix}EndTime` : "endTime"],
      message: "Bitiş zamanı başlangıçtan sonra olmalıdır"
    });
  }
}

function parseLocalDateTime(value: string): number | null {
  if (!value) {
    return null;
  }
  const timestamp = new Date(value).getTime();
  return Number.isNaN(timestamp) ? null : timestamp;
}
