from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from log_parser_engine.batch import BatchParseOptions
from log_parser_engine.core import ParserContext
from log_parser_engine.models import (
    EventAggregationRequest,
    EventQuery,
    LogEvent,
    PipelineOptions,
)
from log_parser_engine.storage import EventWriteOptions


class IngestTextRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    source_name: str | None = None


class ParseRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    raw_log: str
    context: ParserContext | None = None
    options: PipelineOptions = Field(default_factory=PipelineOptions)


class ParseWithParserRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    raw_log: str
    parser_name: str
    context: ParserContext | None = None
    allow_disabled_parser: bool = False


class BatchParseRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    context: ParserContext | None = None
    options: BatchParseOptions = Field(default_factory=BatchParseOptions)


class AddEventRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event: LogEvent
    options: EventWriteOptions = Field(default_factory=EventWriteOptions)


class AddManyEventsRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    events: tuple[LogEvent, ...]
    options: EventWriteOptions = Field(default_factory=EventWriteOptions)


class QueryRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    query: EventQuery = Field(default_factory=EventQuery)


class AggregateRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    request: EventAggregationRequest
    base_query: EventQuery | None = None