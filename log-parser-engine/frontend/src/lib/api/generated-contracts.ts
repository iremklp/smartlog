import type { components } from "./generated/openapi";

export type ApplicationHealth = components["schemas"]["ApplicationHealth"];
export type RuntimeStatistics = components["schemas"]["ApplicationRuntimeStatistics"];
export type EventStoreStatistics = components["schemas"]["StoreStatisticsApiResponse"];
export type ParserRegistration = components["schemas"]["ParserRegistrationApiResponse"];

export type ParseRequest = components["schemas"]["ParseRequest"];
export type ParseWithParserRequest = components["schemas"]["ParseWithParserRequest"];
export type ParseResult = components["schemas"]["ParseResultApiResponse"];
export type PipelineResult = components["schemas"]["PipelineResultApiResponse"];

export type BatchParseRequest = components["schemas"]["BatchParseRequest"];
export type BatchParseResult = components["schemas"]["BatchParseResultApiResponse"];
export type BatchWriteResult = components["schemas"]["BatchWriteResultApiResponse"];

export type LogEvent = components["schemas"]["LogEvent"];
export type StoredEvent = components["schemas"]["StoredEventDetailApiResponse"];
export type EventWriteResult = components["schemas"]["EventWriteResultApiResponse"];

export type EventQuery = components["schemas"]["EventQuery"];
export type EventAggregationRequest = components["schemas"]["EventAggregationRequest"];
export type EventAggregationResult = components["schemas"]["AggregationApiResponse"];
export type EventQueryResult = components["schemas"]["QueryApiResponse"];

export type AnalysisRequest = components["schemas"]["AnalysisApiRequest"];
export type AnalysisResponse = components["schemas"]["AnalysisApiResponse"];
export type ComparisonRequest = components["schemas"]["ComparisonApiRequest"];
export type ComparisonResponse = components["schemas"]["ComparisonApiResponse"];
