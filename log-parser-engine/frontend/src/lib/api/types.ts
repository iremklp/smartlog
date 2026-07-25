export type Primitive = string | number | boolean | null;

export interface ApiErrorShape {
  detail?: string;
}

export interface ApplicationHealth {
  status: "healthy" | "degraded";
  created_at: string;
  checked_at: string;
  uptime_ms: number;
  parser_count: number;
  enabled_parser_count: number;
  store_event_count: number;
  warnings: string[];
}

export interface RuntimeStatistics {
  created_at: string;
  observed_at: string;
  uptime_ms: number;
  parser_count: number;
  enabled_parser_count: number;
  startup_warnings: string[];
  store_statistics: EventStoreStatistics;
}

export interface EventStoreStatistics {
  event_count: number;
  estimated_memory_bytes: number;
  max_events: number;
  max_estimated_memory_bytes: number | null;
  oldest_inserted_at: string | null;
  newest_inserted_at: string | null;
  earliest_event_timestamp: string | null;
  latest_event_timestamp: string | null;
  index_enabled: boolean;
  indexed_field_count: number;
  duplicate_ignored_count: number;
  replaced_count: number;
  evicted_count: number;
  retention_removed_count: number;
  write_count: number;
  query_count: number;
  delete_count: number;
  clear_count: number;
  created_at: string;
  last_write_at: string | null;
  last_query_at: string | null;
  last_retention_at: string | null;
}

export interface ParserRegistration {
  parser_name: string;
  parser_version: string;
  source_type: string;
  enabled: boolean;
  registered_at: string;
  registration_order: number;
  metadata: {
    name: string;
    version: string;
    source_type: string;
    display_name?: string | null;
    supports_batch?: boolean;
    tags?: string[];
  };
  origin: string | null;
  notes: string | null;
}

export interface ParserContextInput {
  source_name?: string | null;
  file_path?: string | null;
  content_type?: string | null;
  encoding?: string;
  strict?: boolean;
  preserve_raw?: boolean;
  attributes?: Record<string, unknown>;
}

export interface ParseRequest {
  raw_log: string;
  context?: ParserContextInput | null;
  options?: Record<string, unknown> | null;
}

export interface ParseWithParserRequest {
  raw_log: string;
  context?: ParserContextInput | null;
  allow_disabled_parser?: boolean;
}

export interface EventWriteOptions {
  event_id?: string | null;
  deduplicate?: boolean | null;
  duplicate_policy?: "ignore" | "replace" | "error" | null;
  apply_retention_before_write?: boolean;
  source_batch_id?: string | null;
  metadata?: Record<string, unknown>;
}

export interface ParseResult {
  status: string;
  events: LogEvent[];
  errors: ParseError[];
}

export interface PipelineResult {
  success: boolean;
  event: LogEvent | null;
  parse_result: ParseResult | null;
  normalization_result: Record<string, unknown> | null;
  selection: Record<string, unknown> | null;
  errors: ParseError[];
  warnings: Array<Record<string, unknown>>;
  stages: Array<Record<string, unknown>>;
  duration_ms: number;
  parser_name: string | null;
  parser_version: string | null;
  source_type: string | null;
  ambiguous: boolean;
  normalized: boolean;
}

export interface ParseError {
  code?: string;
  message: string;
  details?: Record<string, Primitive>;
}

export interface BatchParseRequest {
  text: string;
  context?: ParserContextInput | null;
  options?: Record<string, unknown> | null;
}

export interface BatchParseResult {
  events: LogEvent[];
  failures: BatchItemResult[];
  statistics: BatchParseStatistics;
  sessions: Array<Record<string, unknown>>;
  warnings: string[];
  source_id: string | null;
}

export interface BatchItemResult {
  index: number;
  raw_record?: string | null;
  success: boolean;
  event?: LogEvent | null;
  error?: ParseError | null;
}

export interface BatchParseStatistics {
  records_seen: number;
  records_succeeded: number;
  records_failed: number;
  stopped_early: boolean;
  duration_ms: number;
}

export interface LogEvent {
  timestamp: string;
  severity: string;
  source_type: string;
  raw_log: string;
  event_type?: string | null;
  parser_name?: string | null;
  parser_version?: string | null;
  message?: string | null;
  host?: string | null;
  service?: string | null;
  tags?: string[];
  attributes?: Record<string, Primitive | Primitive[] | Record<string, Primitive>>;
}

export interface StoredEvent {
  id: string;
  event: LogEvent;
  inserted_at: string;
  sequence: number;
  content_hash: string;
  estimated_size_bytes: number;
  source_batch_id: string | null;
  metadata: Record<string, unknown>;
}

export interface EventWriteResult {
  status: "inserted" | "ignored_duplicate" | "replaced";
  stored_event: StoredEvent;
  evicted_event_ids: string[];
}

export interface BatchWriteResult {
  inserted: StoredEvent[];
  ignored_event_ids: string[];
  replaced: StoredEvent[];
  evicted_event_ids: string[];
  errors: string[];
  atomic: boolean;
}

export interface EventQuery {
  filter?: EventFilter;
  sort?: EventSort[];
  offset?: number;
  limit?: number | null;
  include_events?: boolean;
  include_total?: boolean;
  include_facets?: boolean;
  facet_fields?: string[];
  aggregation?: EventAggregationRequest | null;
}

export interface EventFilter {
  message_contains?: string | null;
  severities?: string[];
  source_types?: string[];
  parser_names?: string[];
  hosts?: string[];
  services?: string[];
  tags_any?: string[];
  tags_all?: string[];
  start_time?: string | null;
  end_time?: string | null;
}

export interface EventSort {
  field: string;
  direction: "asc" | "desc";
}

export interface FacetBucket {
  value: string;
  count: number;
}

export interface EventQueryResult {
  events: StoredEvent[];
  page: {
    offset: number;
    limit: number;
    total: number | null;
    has_next: boolean;
  };
  facets: Record<string, FacetBucket[]>;
  aggregation: EventAggregationResult | null;
  query_duration_ms: number;
  snapshot_size: number;
  index_used: boolean;
  candidate_count: number;
  warnings: string[];
}

export type GroupByField =
  | "severity"
  | "source_type"
  | "event_type"
  | "parser_name"
  | "host"
  | "service"
  | "tag"
  | "time_bucket";

export type MetricType = "count" | "average_duration_ms" | "sum_duration_ms";

export interface EventAggregationRequest {
  group_by: GroupByField;
  metric: MetricType;
  time_bucket_seconds?: number | null;
  limit?: number;
}

export interface EventAggregationResult {
  request: EventAggregationRequest;
  buckets: AggregationBucket[];
}

export interface AggregationBucket {
  group_value: string | number;
  event_count: number;
  metric_value: number | null;
  sample_count: number | null;
  bucket_start_time: string | null;
  bucket_end_time: string | null;
}
