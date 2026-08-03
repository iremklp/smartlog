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

const requiredLocalDateTime = (label: string) => z.string().trim().min(1, `${label} zorunludur`);

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

export const COMPARISON_METRIC_OPTIONS = [
  { value: "event_count", label: "Event sayısı" },
  { value: "error_rate", label: "Hata + kritik oranı" },
  { value: "critical_rate", label: "Kritik + fatal oranı" },
  { value: "average_duration_ms", label: "Ortalama süre" },
  { value: "p50_duration_ms", label: "P50 süre" },
  { value: "p95_duration_ms", label: "P95 süre" },
  { value: "p99_duration_ms", label: "P99 süre" },
  { value: "server_error_rate", label: "HTTP 5xx oranı" },
  { value: "client_error_rate", label: "HTTP 4xx oranı" },
  { value: "throughput", label: "Throughput" }
] as const satisfies ReadonlyArray<{ value: ComparisonMetric; label: string }>;

export const COMPARISON_GROUP_OPTIONS = [
  { value: "endpoint", label: "Endpoint" },
  { value: "event_type", label: "Event type" },
  { value: "host", label: "Host" },
  { value: "http_status", label: "HTTP status" },
  { value: "parser_name", label: "Parser" },
  { value: "service", label: "Service" },
  { value: "severity", label: "Severity" }
] as const satisfies ReadonlyArray<{ value: ComparisonGroup; label: string }>;

const comparisonMetricValues = COMPARISON_METRIC_OPTIONS.map((option) => option.value) as [
  ComparisonMetric,
  ...ComparisonMetric[]
];

const comparisonGroupValues = COMPARISON_GROUP_OPTIONS.map((option) => option.value) as [
  ComparisonGroup,
  ...ComparisonGroup[]
];

export const COMPARISON_PERIOD_PRESET_OPTIONS = [
  {
    value: "last_hour",
    label: "Son 1 saat / önceki 1 saat",
    baselineLabel: "Önceki 1 saat",
    comparisonLabel: "Son 1 saat",
    durationMs: 60 * 60 * 1_000
  },
  {
    value: "last_24_hours",
    label: "Son 24 saat / önceki 24 saat",
    baselineLabel: "Önceki 24 saat",
    comparisonLabel: "Son 24 saat",
    durationMs: 24 * 60 * 60 * 1_000
  },
  {
    value: "last_7_days",
    label: "Son 7 gün / önceki 7 gün",
    baselineLabel: "Önceki 7 gün",
    comparisonLabel: "Son 7 gün",
    durationMs: 7 * 24 * 60 * 60 * 1_000
  }
] as const;

export type ComparisonPeriodPreset = (typeof COMPARISON_PERIOD_PRESET_OPTIONS)[number]["value"];

export const comparisonRequestStateSchema = z
  .object({
    baselineLabel: z
      .string()
      .trim()
      .min(1, "Referans etiketi boş olamaz")
      .max(100, "Referans etiketi en fazla 100 karakter olabilir"),
    comparisonLabel: z
      .string()
      .trim()
      .min(1, "Karşılaştırma etiketi boş olamaz")
      .max(100, "Karşılaştırma etiketi en fazla 100 karakter olabilir"),
    baselineStartTime: requiredLocalDateTime("Referans başlangıcı"),
    baselineEndTime: requiredLocalDateTime("Referans bitişi"),
    comparisonStartTime: requiredLocalDateTime("Karşılaştırma başlangıcı"),
    comparisonEndTime: requiredLocalDateTime("Karşılaştırma bitişi"),
    metrics: z.array(z.enum(comparisonMetricValues)).max(10, "En fazla 10 metrik seçilebilir"),
    groupBy: z.array(z.enum(comparisonGroupValues)).max(4, "En fazla dört boyut seçilebilir"),
    topN: z.coerce
      .number()
      .int("Top N tam sayı olmalıdır")
      .min(1, "Top N en az 1 olmalıdır")
      .max(20, "Top N en fazla 20 olabilir")
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

const COMPARISON_REQUEST_BASE_STATE: ComparisonRequestState = {
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

export const DEFAULT_COMPARISON_REQUEST_STATE: ComparisonRequestState = applyComparisonPeriodPreset(
  COMPARISON_REQUEST_BASE_STATE,
  "last_hour"
);

export function applyComparisonPeriodPreset(
  input: ComparisonRequestState,
  preset: ComparisonPeriodPreset,
  now: Date = new Date()
): ComparisonRequestState {
  const nowMilliseconds = now.getTime();
  if (!Number.isFinite(nowMilliseconds)) {
    throw new RangeError("Preset zamanı geçerli olmalıdır");
  }

  const option = COMPARISON_PERIOD_PRESET_OPTIONS.find((item) => item.value === preset);
  if (!option) {
    throw new RangeError("Desteklenmeyen karşılaştırma preseti");
  }

  const comparisonStart = new Date(nowMilliseconds - option.durationMs);
  const baselineStart = new Date(nowMilliseconds - option.durationMs * 2);
  return {
    ...input,
    metrics: [...input.metrics],
    groupBy: [...input.groupBy],
    baselineLabel: option.baselineLabel,
    comparisonLabel: option.comparisonLabel,
    baselineStartTime: toLocalDateTimeInput(baselineStart),
    baselineEndTime: toLocalDateTimeInput(comparisonStart),
    comparisonStartTime: toLocalDateTimeInput(comparisonStart),
    comparisonEndTime: toLocalDateTimeInput(now)
  };
}

export function createDefaultComparisonRequestState(
  now: Date = new Date()
): ComparisonRequestState {
  return applyComparisonPeriodPreset(COMPARISON_REQUEST_BASE_STATE, "last_hour", now);
}

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

function toLocalDateTimeInput(value: Date): string {
  const localMilliseconds = value.getTime() - value.getTimezoneOffset() * 60_000;
  return new Date(localMilliseconds).toISOString().slice(0, 16);
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
