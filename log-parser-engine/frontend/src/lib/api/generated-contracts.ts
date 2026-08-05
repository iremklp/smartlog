import type { components } from "./generated/openapi";

export type ApplicationHealth = components["schemas"]["ApplicationHealth"];
export type RuntimeStatistics = components["schemas"]["ApplicationRuntimeStatistics"];
export type EventStoreStatistics = components["schemas"]["EventStoreStatistics"];
export type ParserRegistration = components["schemas"]["ParserRegistration"];

export type ParseRequest = components["schemas"]["ParseRequest"];
export type ParseWithParserRequest = components["schemas"]["ParseWithParserRequest"];
export type ParseResult = components["schemas"]["ParseResult"];
export type PipelineResult = components["schemas"]["PipelineResult"];

export type BatchParseRequest = components["schemas"]["BatchParseRequest"];
export type BatchParseResult = components["schemas"]["BatchParseResult"];
export type BatchWriteResult = components["schemas"]["BatchWriteResult"];

export type LogEvent = components["schemas"]["LogEvent"];
export type StoredEvent = components["schemas"]["StoredEvent"];
export type EventWriteResult = components["schemas"]["EventWriteResult"];

export type EventQuery = components["schemas"]["EventQuery"];
export type EventAggregationRequest = components["schemas"]["EventAggregationRequest"];
export type EventAggregationResult = components["schemas"]["EventAggregationResult"];
export type EventQueryResult = components["schemas"]["EventQueryResult"];

export type AnalysisRequest = components["schemas"]["AnalysisApiRequest"];
export type AnalysisResponse = components["schemas"]["AnalysisApiResponse"];
export type ComparisonRequest = components["schemas"]["ComparisonApiRequest"];
export type ComparisonResponse = components["schemas"]["ComparisonApiResponse"];
