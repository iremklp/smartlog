export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonObject | JsonValue[];
export interface JsonObject {
  [key: string]: JsonValue;
}

export interface ApiErrorShape {
  detail?: unknown;
  error?: {
    code?: unknown;
    message?: unknown;
    request_id?: unknown;
    details?: unknown;
  };
}

export type LogSeverity =
  "trace" | "debug" | "info" | "notice" | "warning" | "error" | "critical" | "fatal" | "unknown";

export type LogSourceType =
  | "file"
  | "syslog"
  | "http"
  | "database"
  | "windows_event"
  | "application"
  | "iis"
  | "redis"
  | "json"
  | "xml"
  | "csv"
  | "nginx"
  | "apache"
  | "linux_syslog"
  | "kubernetes"
  | "openshift"
  | "jenkins"
  | "unknown";

export type ParseStatus = "success" | "failed" | "partial";

export type ErrorType =
  | "unknown"
  | "parsing"
  | "validation"
  | "ingestion"
  | "unknown_format"
  | "empty_input"
  | "internal_error"
  | "detection_failed"
  | "parse_failed"
  | "validation_failed"
  | "invalid_timestamp"
  | "invalid_encoding";

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
  analysis_operations_total: number;
  analysis_operations_failed: number;
  comparison_operations_total: number;
  comparison_operations_failed: number;
  analyzed_events_total: number;
  average_analysis_duration_ms: number;
  maximum_analysis_duration_ms: number;
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

export interface ParserMetadata {
  name: string;
  display_name: string;
  version: string;
  source_type: LogSourceType;
  description: string | null;
  author: string | null;
  homepage: string | null;
  supported_extensions: string[];
  supported_content_types: string[];
  priority: number;
  enabled_by_default: boolean;
  supports_multiline: boolean;
  supports_batch: boolean;
  thread_safe: boolean;
  experimental: boolean;
  tags: string[];
}

export interface ParserRegistration {
  parser_name: string;
  parser_version: string;
  source_type: LogSourceType;
  enabled: boolean;
  registered_at: string;
  registration_order: number;
  metadata: ParserMetadata;
  origin: string | null;
  notes: string | null;
}

export interface ParserContextInput {
  source_name?: string | null;
  file_path?: string | null;
  content_type?: string | null;
  encoding?: string;
  line_number?: number | null;
  environment?: string | null;
  application?: string | null;
  service?: string | null;
  host?: string | null;
  strict?: boolean;
  preserve_raw?: boolean;
  attributes?: JsonObject;
}

export interface ParseRequest {
  raw_log: string;
  context?: ParserContextInput | null;
  options?: JsonObject;
}

export interface ParseWithParserRequest {
  raw_log: string;
  context?: ParserContextInput | null;
  allow_disabled_parser?: boolean;
}

export type DuplicatePolicy = "reject" | "ignore" | "replace";

export interface EventWriteOptions {
  event_id?: string | null;
  deduplicate?: boolean | null;
  duplicate_policy?: DuplicatePolicy | null;
  apply_retention_before_write?: boolean;
  source_batch_id?: string | null;
  metadata?: JsonObject;
}

export interface ParseError {
  message: string;
  status: ParseStatus;
  error_type: ErrorType;
  details: Record<string, string> | null;
}

export interface ParseResult {
  status: ParseStatus;
  events: LogEvent[];
  errors: ParseError[];
}

export interface PipelineResult {
  success: boolean;
  event: LogEvent | null;
  parse_result: ParseResult | null;
  normalization_result: JsonObject | null;
  selection: JsonObject | null;
  errors: ParseError[];
  warnings: JsonObject[];
  stages: JsonObject[];
  duration_ms: number;
  parser_name: string | null;
  parser_version: string | null;
  source_type: LogSourceType | null;
  ambiguous: boolean;
  normalized: boolean;
}

export interface BatchParseRequest {
  text: string;
  context?: ParserContextInput | null;
  options?: JsonObject;
}

export type BatchRecordType = "data" | "header" | "comment" | "blank" | "document";
export type BatchItemStatus = "success" | "failure" | "skipped" | "header" | "comment";

export interface BatchItem {
  index: number;
  source_line_start: number | null;
  source_line_end: number | null;
  raw_record: string | null;
  raw_record_preview: string | null;
  record_type: BatchRecordType;
  context_attributes: JsonObject;
  character_count: number;
}

export interface BatchItemResult {
  item: BatchItem;
  status: BatchItemStatus;
  parser_name: string | null;
  event: LogEvent | null;
  parse_result: ParseResult | null;
  error_code: string | null;
  error_message: string | null;
  duration_ms: number | null;
  detection_performed: boolean;
  redetection_performed: boolean;
  state_updates: JsonObject;
  attributes: JsonObject;
}

export interface BatchParseStatistics {
  records_seen: number;
  records_attempted: number;
  records_succeeded: number;
  records_failed: number;
  records_skipped: number;
  headers_seen: number;
  comments_seen: number;
  blank_records_seen: number;
  events_collected: number;
  failures_collected: number;
  failures_dropped: number;
  parser_detection_count: number;
  parser_redetection_count: number;
  parser_switch_count: number;
  bytes_or_characters_processed: number;
  max_record_characters_seen: number;
  total_duration_ms: number;
  detection_duration_ms: number;
  parsing_duration_ms: number;
  earliest_event_timestamp: string | null;
  latest_event_timestamp: string | null;
  stopped_early: boolean;
  stop_reason: string | null;
  parser_counts: Record<string, number>;
  error_counts: Record<string, number>;
  status_counts: Record<string, number>;
}

export interface ParserSessionInfo {
  parser_name: string;
  parser_version: string;
  selected_by: "explicit" | "detection" | "redetection";
  detection_confidence: number | null;
  detection_reason: string | null;
  started_at_record: number;
  ended_at_record: number | null;
  records_attempted: number;
  records_succeeded: number;
  records_failed: number;
  stateful: boolean;
  attributes: JsonObject;
}

export interface BatchParseResult {
  events: LogEvent[];
  failures: BatchItemResult[];
  statistics: BatchParseStatistics;
  sessions: ParserSessionInfo[];
  warnings: string[];
  source_id: string | null;
}

export interface LogEvent {
  schema_version: string;
  event_id: string;
  timestamp: string;
  ingested_at: string;
  source_type: LogSourceType;
  severity: LogSeverity;
  event_type: string | null;
  message: string;
  raw_message: string;
  service: string | null;
  application: string | null;
  environment: string | null;
  host: string | null;
  source: string | null;
  trace_id: string | null;
  correlation_id: string | null;
  user_id: string | null;
  client_ip: string | null;
  server_ip: string | null;
  http_method: string | null;
  http_path: string | null;
  http_status: number | null;
  duration_ms: number | null;
  attributes: JsonObject;
  tags: string[];
}

export interface StoredEvent {
  id: string;
  event: LogEvent;
  inserted_at: string;
  sequence: number;
  content_hash: string;
  estimated_size_bytes: number;
  source_batch_id: string | null;
  metadata: JsonObject;
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

export interface EventFilter {
  event_ids?: string[];
  exclude_event_ids?: string[];
  start_time?: string | null;
  end_time?: string | null;
  severities?: LogSeverity[];
  source_types?: LogSourceType[];
  event_types?: string[];
  parser_names?: string[];
  hosts?: string[];
  services?: string[];
  tags_any?: string[];
  tags_all?: string[];
  message_contains?: string | null;
  message_case_sensitive?: boolean;
  client_ips?: string[];
  user_ids?: string[];
  correlation_ids?: string[];
  attribute_exists?: string[];
  attribute_equals?: Record<string, JsonPrimitive>;
}

export type EventSortField =
  "timestamp" | "inserted_at" | "sequence" | "severity" | "event_type" | "host";

export interface EventSort {
  field: EventSortField;
  direction: "asc" | "desc";
}

export type FacetField =
  "severity" | "source_type" | "event_type" | "parser_name" | "host" | "service" | "tags";

export interface EventQuery {
  filter?: EventFilter;
  sort?: EventSort[];
  offset?: number;
  limit?: number | null;
  include_events?: boolean;
  include_total?: boolean;
  include_facets?: boolean;
  facet_fields?: FacetField[];
  include_null_facet?: boolean;
  aggregation?: EventAggregationRequest | null;
}

export interface EventPage {
  offset: number;
  limit: number;
  returned: number;
  total: number | null;
}

export interface FacetBucket {
  value: string;
  count: number;
}

export interface EventQueryResult {
  events: StoredEvent[];
  page: EventPage;
  facets: Partial<Record<FacetField, FacetBucket[]>>;
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

export interface AggregationBucket {
  group_value: string | number;
  event_count: number;
  metric_value: number | null;
  sample_count: number | null;
  bucket_start_time: string | null;
  bucket_end_time: string | null;
}

export interface EventAggregationResult {
  request: EventAggregationRequest;
  buckets: AggregationBucket[];
}

export type AnalysisGroupField =
  | "severity"
  | "source_type"
  | "event_type"
  | "parser_name"
  | "parser"
  | "service"
  | "host"
  | "tags"
  | "tag"
  | "http_method"
  | "method"
  | "http_status"
  | "status_code"
  | "status_class"
  | "endpoint";

export interface AnalysisRequest {
  filter?: EventFilter | null;
  start_time?: string | null;
  end_time?: string | null;
  time_bucket_seconds?: number | null;
  group_fields?: AnalysisGroupField[];
  top_n?: number | null;
  percentiles?: number[];
  include_summary?: boolean;
  include_distributions?: boolean;
  include_timeline?: boolean;
  include_latency?: boolean;
  include_http?: boolean;
  include_insights?: boolean;
  include_samples?: boolean;
  sample_size?: number;
  duration_field?: string | null;
  status_field?: string | null;
  method_field?: string | null;
  path_field?: string | null;
  metadata?: JsonObject;
}

export interface AnalysisSummary {
  input_event_count: number;
  matched_event_count: number;
  trace_count: number;
  debug_count: number;
  info_count: number;
  warning_count: number;
  error_count: number;
  critical_count: number;
  unknown_count: number;
  error_or_critical_count: number;
  error_rate: number;
  critical_rate: number;
  unique_event_type_count: number;
  unique_service_count: number;
  unique_host_count: number;
  unique_parser_count: number;
  unique_source_type_count: number;
  earliest_timestamp: string | null;
  latest_timestamp: string | null;
  time_span_seconds: number | null;
  events_per_second: number | null;
  events_per_minute: number | null;
  events_with_duration: number;
  events_with_http_status: number;
  duplicate_content_count: number;
  out_of_order_timestamp_count: number;
}

export interface RankedItem {
  rank: number;
  key: string;
  display_value: string;
  count: number;
  percentage: number;
  metric_value: number | null;
  metric_unit: string | null;
  attributes: JsonObject;
}

export interface DistributionResult {
  field: string;
  total_count: number;
  matched_value_count: number;
  missing_count: number;
  unique_value_count: number;
  items: RankedItem[];
  other_count: number;
  truncated: boolean;
}

export interface TimelineBucket {
  start: string;
  end: string;
  event_count: number;
  warning_count: number;
  error_count: number;
  critical_count: number;
  error_rate: number;
  average_duration_ms: number | null;
  p95_duration_ms: number | null;
  status_5xx_count: number;
}

export interface TimelineResult {
  bucket_seconds: number;
  start: string | null;
  end: string | null;
  buckets: TimelineBucket[];
  empty_bucket_count: number;
  max_bucket_event_count: number;
  average_bucket_event_count: number;
  peak_bucket_start: string | null;
  warnings: string[];
}

export interface PercentileSummary {
  sample_count: number;
  minimum: number | null;
  maximum: number | null;
  mean: number | null;
  median: number | null;
  standard_deviation: number | null;
  percentile_values: Record<string, number | null>;
  missing_count: number;
  invalid_count: number;
  percentile_sample_count: number | null;
  percentiles_approximated: boolean;
}

export interface LatencyBucket {
  lower_bound_ms: number | null;
  upper_bound_ms: number | null;
  count: number;
  percentage: number;
  label: string;
}

export interface SlowEvent {
  event_id: string;
  timestamp: string;
  duration_ms: number;
  event_type: string | null;
  service: string | null;
  host: string | null;
  path: string | null;
  message_preview: string | null;
}

export interface EndpointLatency {
  key: string;
  sample_count: number;
  minimum_ms: number | null;
  maximum_ms: number | null;
  mean_ms: number | null;
  p95_ms: number | null;
  missing_count: number;
}

export interface LatencyAnalysis {
  detected_field: string | null;
  unit: string;
  total_events: number;
  sample_count: number;
  missing_count: number;
  invalid_count: number;
  minimum_ms: number | null;
  maximum_ms: number | null;
  mean_ms: number | null;
  median_ms: number | null;
  standard_deviation_ms: number | null;
  percentiles: PercentileSummary;
  slowest_events: SlowEvent[];
  latency_buckets: LatencyBucket[];
  per_service: EndpointLatency[];
  per_event_type: EndpointLatency[];
  per_endpoint: EndpointLatency[];
  warnings: string[];
}

export interface HTTPStatusBreakdown {
  key: string;
  total_count: number;
  informational_count: number;
  success_count: number;
  redirect_count: number;
  client_error_count: number;
  server_error_count: number;
  unknown_status_count: number;
  error_rate: number;
}

export interface EndpointAnalysis {
  endpoint: string;
  request_count: number;
  percentage: number;
  error_count: number;
  error_rate: number;
  client_error_count: number;
  server_error_count: number;
  latency_sample_count: number;
  average_duration_ms: number | null;
  p95_duration_ms: number | null;
  max_duration_ms: number | null;
  methods: string[];
  top_status_codes: RankedItem[];
  services: string[];
  first_seen: string | null;
  last_seen: string | null;
  attributes: JsonObject;
}

export interface HTTPAnalysis {
  http_event_count: number;
  events_with_status: number;
  events_with_method: number;
  events_with_path: number;
  informational_count: number;
  success_count: number;
  redirect_count: number;
  non_error_count: number;
  client_error_count: number;
  server_error_count: number;
  unknown_status_count: number;
  success_rate: number;
  non_error_rate: number;
  client_error_rate: number;
  server_error_rate: number;
  total_error_rate: number;
  status_class_distribution: DistributionResult;
  status_code_distribution: DistributionResult;
  method_distribution: DistributionResult;
  endpoint_distribution: DistributionResult;
  slowest_endpoints: EndpointAnalysis[];
  highest_error_endpoints: EndpointAnalysis[];
  status_by_method: HTTPStatusBreakdown[];
  status_by_service: HTTPStatusBreakdown[];
  timeline: TimelineResult | null;
  warnings: string[];
}

export type AnalysisInsightLevel = "info" | "warning" | "critical";

export interface AnalysisInsight {
  code: string;
  level: AnalysisInsightLevel;
  title: string;
  message: string;
  metric: string | null;
  current_value: number | null;
  reference_value: number | null;
  unit: string | null;
  evidence: JsonObject;
  recommendations: string[];
}

export interface AnalysisEventSample {
  event_id: string;
  timestamp: string;
  severity: LogSeverity;
  source_type: LogSourceType;
  message_preview: string;
  event_type: string | null;
  service: string | null;
  host: string | null;
  parser_name: string | null;
}

export interface AnalysisResponse {
  analysis_id: string;
  generated_at: string;
  input_event_count: number;
  matched_event_count: number;
  analysis_duration_ms: number;
  summary: AnalysisSummary | null;
  timeline: TimelineResult | null;
  distributions: DistributionResult[];
  latency: LatencyAnalysis | null;
  http: HTTPAnalysis | null;
  insights: AnalysisInsight[];
  samples: AnalysisEventSample[];
  warnings: string[];
}

export type ComparisonMetric =
  | "event_count"
  | "error_rate"
  | "critical_rate"
  | "average_duration_ms"
  | "p50_duration_ms"
  | "p95_duration_ms"
  | "p99_duration_ms"
  | "server_error_rate"
  | "client_error_rate"
  | "throughput";

export type ComparisonGroup =
  | "endpoint"
  | "event_type"
  | "host"
  | "http_status"
  | "parser"
  | "parser_name"
  | "service"
  | "severity"
  | "status_code";

export type ComparisonGroupField = ComparisonGroup;

export interface ComparisonRequest {
  baseline_filter?: EventFilter | null;
  comparison_filter?: EventFilter | null;
  baseline_label?: string;
  comparison_label?: string;
  metrics?: ComparisonMetric[];
  group_by?: ComparisonGroupField[];
  top_n?: number;
  minimum_group_count?: number;
  significant_change_percent?: number | null;
  normalize_by_time_span?: boolean;
  include_new_groups?: boolean;
  include_disappeared_groups?: boolean;
  metadata?: JsonObject;
}

export type ChangeDirection =
  "increase" | "decrease" | "unchanged" | "new" | "removed" | "undefined";

export type MetricInterpretation = "improved" | "degraded" | "neutral" | "unknown";

export interface MetricComparison {
  metric: string;
  unit: string | null;
  baseline_value: number | null;
  comparison_value: number | null;
  absolute_change: number | null;
  percent_change: number | null;
  direction: ChangeDirection;
  significant: boolean;
  interpretation: MetricInterpretation;
  notes: string[];
}

export interface GroupComparison {
  group_field: string;
  key: string;
  baseline_count: number;
  comparison_count: number;
  absolute_change: number;
  percent_change: number | null;
  baseline_percentage: number;
  comparison_percentage: number;
  percentage_point_change: number;
  new_group: boolean;
  disappeared_group: boolean;
  significant: boolean;
  metric_comparisons: MetricComparison[];
  attributes: JsonObject;
}

export interface ComparisonResponse {
  baseline_label: string;
  comparison_label: string;
  baseline_summary: AnalysisSummary;
  comparison_summary: AnalysisSummary;
  baseline_event_count: number;
  comparison_event_count: number;
  duration_ms: number;
  metric_comparisons: MetricComparison[];
  group_comparisons: GroupComparison[];
  insights: AnalysisInsight[];
  warnings: string[];
}
