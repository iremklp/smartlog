from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from log_parser_engine.models import (
    AnalysisResult,
    BatchParseResult,
    BatchWriteResult,
    ComparisonResult,
    EventQueryResult,
    EventWriteResult,
    IngestionResult,
    PipelineResult,
)


class ParseExecutionResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    result: PipelineResult
    stored_event_id: str | None = None


class BatchExecutionResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    result: BatchParseResult
    write_result: BatchWriteResult | None = None


class StoreExecutionResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    write_result: EventWriteResult | BatchWriteResult


class IngestionExecutionResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    result: IngestionResult


class QueryExecutionResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    result: EventQueryResult


class AnalyzeEventsResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    result: AnalysisResult


class CompareEventsResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    result: ComparisonResult
