import { z } from "zod";

import type {
  AnalysisResponse,
  ComparisonResponse,
  EventQueryResult
} from "./types";

const eventPageSchema = z.object({
  offset: z.number(),
  limit: z.number(),
  returned: z.number(),
  total: z.number().nullable()
});

const logEventSchema = z
  .object({
    message: z.string(),
    raw_message: z.string()
  })
  .passthrough();

const storedEventSchema = z
  .object({
    id: z.string(),
    event: logEventSchema
  })
  .passthrough();

const analysisResponseSchema = z
  .object({
    analysis_id: z.string(),
    generated_at: z.string(),
    input_event_count: z.number(),
    matched_event_count: z.number(),
    analysis_duration_ms: z.number(),
    summary: z.unknown().nullable(),
    timeline: z.unknown().nullable(),
    distributions: z.array(z.unknown()).default([]),
    latency: z.unknown().nullable(),
    http: z.unknown().nullable(),
    insights: z.array(z.unknown()).default([]),
    samples: z.array(z.unknown()).default([]),
    warnings: z.array(z.string()).default([])
  })
  .passthrough();

const comparisonResponseSchema = z
  .object({
    baseline_label: z.string(),
    comparison_label: z.string(),
    baseline_summary: z.unknown(),
    comparison_summary: z.unknown(),
    baseline_event_count: z.number(),
    comparison_event_count: z.number(),
    duration_ms: z.number(),
    metric_comparisons: z.array(z.unknown()).default([]),
    group_comparisons: z.array(z.unknown()).default([]),
    insights: z.array(z.unknown()).default([]),
    warnings: z.array(z.string()).default([])
  })
  .passthrough();

const eventQueryResultSchema = z
  .object({
    events: z.array(storedEventSchema).default([]),
    page: eventPageSchema,
    facets: z.record(z.array(z.unknown())).default({}),
    aggregation: z.unknown().nullable().optional().default(null),
    query_duration_ms: z.number(),
    snapshot_size: z.number(),
    index_used: z.boolean(),
    candidate_count: z.number(),
    warnings: z.array(z.string()).default([])
  })
  .passthrough();

function validateContract<T>(
  endpoint: string,
  schema: z.ZodTypeAny,
  payload: unknown
): T {
  const parsed = schema.safeParse(payload);
  if (parsed.success) {
    return parsed.data as T;
  }

  const issue = parsed.error.issues[0];
  const path = issue?.path?.join(".") || "root";
  const message = issue?.message || "unknown contract validation error";
  throw new Error(
    `Contract validation failed for ${endpoint}: ${path} ${message}`
  );
}

export function validateAnalysisResponse(payload: unknown): AnalysisResponse {
  return validateContract<AnalysisResponse>(
    "/api/v1/analysis",
    analysisResponseSchema,
    payload
  );
}

export function validateComparisonResponse(payload: unknown): ComparisonResponse {
  return validateContract<ComparisonResponse>(
    "/api/v1/analysis/compare",
    comparisonResponseSchema,
    payload
  );
}

export function validateEventQueryResult(payload: unknown): EventQueryResult {
  return validateContract<EventQueryResult>(
    "/query",
    eventQueryResultSchema,
    payload
  );
}
