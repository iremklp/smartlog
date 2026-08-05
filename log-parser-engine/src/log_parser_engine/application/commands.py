from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from log_parser_engine.batch import BatchParseOptions
from log_parser_engine.core import ParserContext
from log_parser_engine.models import (
    AnalysisRequest,
    ComparisonRequest,
    EventAggregationRequest,
    EventQuery,
    LogEvent,
    PipelineOptions,
)
from log_parser_engine.storage import EventWriteOptions


class IngestTextCommand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    source_name: str | None = None


class IngestBytesCommand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    data: bytes
    source_name: str | None = None


class IngestPathCommand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    path: Path


class ParseTextCommand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    raw_log: str
    context: ParserContext | None = None
    options: PipelineOptions = Field(default_factory=PipelineOptions)
    parser_name: str | None = None
    store_result: bool = False
    batch_mode: bool = False
    allow_disabled_parser: bool = False


class ParseBytesCommand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    data: bytes
    source_name: str | None = None
    file_name: str | None = None
    content_type: str | None = None
    options: PipelineOptions = Field(default_factory=PipelineOptions)
    parser_name: str | None = None
    store_result: bool = False
    batch_mode: bool = False
    allow_disabled_parser: bool = False


class ParseWithParserCommand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    parser_name: str
    raw_log: str
    context: ParserContext | None = None
    options: PipelineOptions = Field(default_factory=PipelineOptions)


class BatchParseTextCommand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    context: ParserContext | None = None
    options: BatchParseOptions = Field(default_factory=BatchParseOptions)


class BatchParseLinesCommand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    lines: tuple[str, ...]
    context: ParserContext | None = None
    options: BatchParseOptions = Field(default_factory=BatchParseOptions)


class AddEventCommand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event: LogEvent
    options: EventWriteOptions = Field(default_factory=EventWriteOptions)


class AddManyEventsCommand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    events: tuple[LogEvent, ...]
    options: EventWriteOptions = Field(default_factory=EventWriteOptions)


class QueryEventsCommand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    query: EventQuery = Field(default_factory=EventQuery)


class AggregateEventsCommand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    request: EventAggregationRequest


class AnalyzeEventsCommand(BaseModel):
    """Request an analysis over the application store's immutable snapshot."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    request: AnalysisRequest = Field(default_factory=AnalysisRequest)


class CompareEventsCommand(BaseModel):
    """Compare two filtered views of the same immutable store snapshot."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    request: ComparisonRequest = Field(default_factory=ComparisonRequest)
