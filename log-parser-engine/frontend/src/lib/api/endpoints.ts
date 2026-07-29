import { requestJson } from "./client";
import type {
  AnalysisRequest,
  AnalysisResponse,
  ApplicationHealth,
  BatchParseRequest,
  BatchParseResult,
  BatchWriteResult,
  ComparisonRequest,
  ComparisonResponse,
  EventAggregationRequest,
  EventAggregationResult,
  EventQuery,
  EventQueryResult,
  EventStoreStatistics,
  EventWriteResult,
  ParseRequest,
  ParseResult,
  ParseWithParserRequest,
  ParserRegistration,
  PipelineResult,
  RuntimeStatistics,
  LogEvent,
  StoredEvent
} from "./types";

export function getHealth(signal?: AbortSignal) {
  return requestJson<ApplicationHealth>("/health", { method: "GET" }, signal);
}

export function getRuntimeStatistics(signal?: AbortSignal) {
  return requestJson<RuntimeStatistics>("/runtime/statistics", { method: "GET" }, signal);
}

export function getStoreStatistics(signal?: AbortSignal) {
  return requestJson<EventStoreStatistics>("/store/statistics", { method: "GET" }, signal);
}

export function listParsers(signal?: AbortSignal) {
  return requestJson<ParserRegistration[]>("/parsers", { method: "GET" }, signal);
}

export function parseText(payload: ParseRequest, signal?: AbortSignal) {
  return requestJson<PipelineResult>(
    "/parse",
    { method: "POST", body: JSON.stringify(payload) },
    signal
  );
}

export function parseWithParser(
  parserName: string,
  payload: ParseWithParserRequest,
  signal?: AbortSignal
) {
  return requestJson<ParseResult>(
    `/parse/${encodeURIComponent(parserName)}`,
    { method: "POST", body: JSON.stringify(payload) },
    signal
  );
}

export function parseAndStoreText(payload: ParseRequest, signal?: AbortSignal) {
  return requestJson<EventWriteResult>(
    "/parse/store",
    { method: "POST", body: JSON.stringify(payload) },
    signal
  );
}

export function addEvent(event: LogEvent, signal?: AbortSignal) {
  return requestJson<EventWriteResult>(
    "/events",
    { method: "POST", body: JSON.stringify({ event }) },
    signal
  );
}

export function batchParseText(payload: BatchParseRequest, signal?: AbortSignal) {
  return requestJson<BatchParseResult>(
    "/batch/parse",
    { method: "POST", body: JSON.stringify(payload) },
    signal
  );
}

export function batchParseAndStoreText(payload: BatchParseRequest, signal?: AbortSignal) {
  return requestJson<BatchWriteResult>(
    "/batch/parse/store",
    { method: "POST", body: JSON.stringify(payload) },
    signal
  );
}

export async function parseFile(
  file: File,
  options: {
    sourceName?: string;
    parserName?: string;
    storeResult?: boolean;
    batchMode?: boolean;
    allowDisabledParser?: boolean;
  } = {},
  signal?: AbortSignal
): Promise<PipelineResult | ParseResult | BatchParseResult | EventWriteResult | BatchWriteResult> {
  const formData = new FormData();
  formData.set("file", file);
  if (options.sourceName) {
    formData.set("source_name", options.sourceName);
  }
  if (options.parserName) {
    formData.set("parser_name", options.parserName);
  }
  formData.set("store_result", String(Boolean(options.storeResult)));
  formData.set("batch_mode", String(Boolean(options.batchMode)));
  formData.set("allow_disabled_parser", String(Boolean(options.allowDisabledParser)));

  return requestJson<
    PipelineResult | ParseResult | BatchParseResult | EventWriteResult | BatchWriteResult
  >(
    "/parse/file",
    {
      method: "POST",
      body: formData
    },
    signal
  );
}

export function queryEvents(query: EventQuery, signal?: AbortSignal) {
  return requestJson<EventQueryResult>(
    "/query",
    { method: "POST", body: JSON.stringify({ query }) },
    signal
  );
}

export function aggregateEvents(
  request: EventAggregationRequest,
  baseQuery?: EventQuery,
  signal?: AbortSignal
) {
  return requestJson<EventAggregationResult | null>(
    "/aggregate",
    { method: "POST", body: JSON.stringify({ request, base_query: baseQuery ?? null }) },
    signal
  );
}

export function analyzeEvents(payload: AnalysisRequest, signal?: AbortSignal) {
  return requestJson<AnalysisResponse>(
    "/api/v1/analysis",
    { method: "POST", body: JSON.stringify(payload) },
    signal
  );
}

export function compareEvents(payload: ComparisonRequest, signal?: AbortSignal) {
  return requestJson<ComparisonResponse>(
    "/api/v1/analysis/compare",
    { method: "POST", body: JSON.stringify(payload) },
    signal
  );
}

export function getEventById(eventId: string, signal?: AbortSignal) {
  return requestJson<StoredEvent>(
    `/events/${encodeURIComponent(eventId)}`,
    { method: "GET" },
    signal
  );
}

export function deleteEventById(eventId: string, signal?: AbortSignal) {
  return requestJson<{ deleted: boolean }>(
    `/events/${encodeURIComponent(eventId)}`,
    { method: "DELETE" },
    signal
  );
}
