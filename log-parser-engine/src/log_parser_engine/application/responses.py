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
    ParseResult,
    PipelineResult,
)


class ParseExecutionResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    result: PipelineResult
    stored_event_id: str | None = None


class ParseOperationResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    result: (
        PipelineResult
        | ParseResult
        | BatchParseResult
        | EventWriteResult
        | BatchWriteResult
    )


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


class PublicApiIdentityResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    version: str
    environment: str


class PublicApiLimitsResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    max_upload_bytes: int
    max_text_characters: int
    max_page_size: int
    max_response_items: int


class PublicApiCapabilitiesResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    can_clear_store: bool
    can_delete_events: bool
    includes_raw_message_in_event_detail: bool
    includes_runtime_metrics: bool
    supports_file_upload: bool
    requires_authentication: bool
    uses_persistent_storage: bool


class PublicApiConfigResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    app: PublicApiIdentityResponse
    limits: PublicApiLimitsResponse
    capabilities: PublicApiCapabilitiesResponse
