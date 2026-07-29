from __future__ import annotations

import math
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from log_parser_engine.analysis import AnalysisOptions
from log_parser_engine.batch import BatchParseOptions
from log_parser_engine.core import ParserContext
from log_parser_engine.models import (
    AnalysisEventSample,
    AnalysisInsight,
    AnalysisRequest,
    AnalysisResult,
    AnalysisSummary,
    ComparisonRequest,
    ComparisonResult,
    DistributionResult,
    EventAggregationRequest,
    EventQuery,
    GroupComparison,
    HTTPAnalysis,
    LatencyAnalysis,
    LogEvent,
    MetricComparison,
    PipelineOptions,
    TimelineResult,
)
from log_parser_engine.models.analysis_request import SAFE_GROUPS
from log_parser_engine.storage import EventWriteOptions

_MAX_RESPONSE_TEXT_LENGTH = 1_000
_MAX_EVIDENCE_ITEMS = 32
_MAX_JSON_DEPTH = 12
_BOUNDED_CONTAINER_KEYS = frozenset({"attributes", "evidence"})
_DIMENSION_KEYS = frozenset(
    {
        "detected_field",
        "display_value",
        "endpoint",
        "event_type",
        "field",
        "group_field",
        "host",
        "key",
        "method",
        "parser_name",
        "path",
        "service",
        "source_type",
    }
)
_EXCLUDED_RESPONSE_KEYS = frozenset(
    {
        "baseline_filter",
        "comparison_filter",
        "filter",
        "message_contains",
        "metadata",
        "raw_message",
        "request",
    }
)


def _bounded_text(value: str, *, limit: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    if limit <= 1:
        return normalized[:limit]
    return f"{normalized[: limit - 1]}…"


def _safe_json_value(
    value: object,
    *,
    key: str | None = None,
    depth: int = 0,
    dimension_limit: int,
    bounded_container: bool = False,
) -> Any:
    """Return a bounded JSON-safe copy suitable for the public API."""

    if depth > _MAX_JSON_DEPTH:
        if isinstance(value, dict):
            return {}
        if isinstance(value, (list, tuple)):
            return []
        if isinstance(value, str):
            return _bounded_text(value, limit=_MAX_RESPONSE_TEXT_LENGTH)
        if value is None or isinstance(value, (bool, int)):
            return value
        if isinstance(value, float):
            return value if math.isfinite(value) else None
        return None
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, str):
        limit = (
            dimension_limit
            if key in _DIMENSION_KEYS
            else _MAX_RESPONSE_TEXT_LENGTH
        )
        return _bounded_text(value, limit=limit)
    if isinstance(value, (list, tuple)):
        should_bound = bounded_container or key in _BOUNDED_CONTAINER_KEYS
        items = (
            value[:_MAX_EVIDENCE_ITEMS]
            if should_bound
            else value
        )
        return [
            _safe_json_value(
                item,
                depth=depth + 1,
                dimension_limit=dimension_limit,
                bounded_container=should_bound,
            )
            for item in items
        ]
    if isinstance(value, dict):
        should_bound = bounded_container or key in _BOUNDED_CONTAINER_KEYS
        result: dict[str, Any] = {}
        items = list(value.items())
        if should_bound:
            items = items[:_MAX_EVIDENCE_ITEMS]
        for raw_key, item in items:
            safe_key = str(raw_key)
            if safe_key in _EXCLUDED_RESPONSE_KEYS:
                continue
            result[safe_key] = _safe_json_value(
                item,
                key=safe_key,
                depth=depth + 1,
                dimension_limit=dimension_limit,
                bounded_container=should_bound,
            )
        return result
    return _bounded_text(str(value), limit=_MAX_RESPONSE_TEXT_LENGTH)


def _safe_model_payload(
    model: BaseModel,
    *,
    options: AnalysisOptions,
    exclude: set[str] | None = None,
) -> dict[str, Any]:
    dumped = model.model_dump(mode="json", exclude=exclude or set())
    safe = _safe_json_value(
        dumped,
        dimension_limit=options.max_dimension_value_length,
    )
    if not isinstance(safe, dict):  # pragma: no cover - model dumps are mappings
        raise TypeError("public analysis payload must be an object")
    return safe


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


class AnalysisApiRequest(AnalysisRequest):
    """Version-one HTTP schema for statistical analysis requests."""

    @field_validator("group_fields")
    @classmethod
    def _public_group_fields(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        unsupported = tuple(field for field in value if field not in SAFE_GROUPS)
        if unsupported:
            raise ValueError(
                "public analysis group fields must use supported dimensions"
            )
        return value


class ComparisonApiRequest(ComparisonRequest):
    """Version-one HTTP schema for period comparison requests."""


class AnalysisApiResponse(BaseModel):
    """Safe public analysis response without request or user metadata echo."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    analysis_id: UUID
    generated_at: datetime
    input_event_count: int
    matched_event_count: int
    analysis_duration_ms: float
    summary: AnalysisSummary | None = None
    timeline: TimelineResult | None = None
    distributions: tuple[DistributionResult, ...] = ()
    latency: LatencyAnalysis | None = None
    http: HTTPAnalysis | None = None
    insights: tuple[AnalysisInsight, ...] = ()
    samples: tuple[AnalysisEventSample, ...] = ()
    warnings: tuple[str, ...] = ()

    @classmethod
    def from_domain(
        cls,
        result: AnalysisResult,
        *,
        options: AnalysisOptions,
    ) -> "AnalysisApiResponse":
        """Map a domain result to a bounded response, omitting request details."""

        payload = _safe_model_payload(
            result,
            options=options,
            exclude={"request", "metadata"},
        )
        return cls.model_validate(payload)


class ComparisonApiResponse(BaseModel):
    """Safe public comparison response without user metadata echo."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    baseline_label: str
    comparison_label: str
    baseline_summary: AnalysisSummary
    comparison_summary: AnalysisSummary
    baseline_event_count: int
    comparison_event_count: int
    duration_ms: float
    metric_comparisons: tuple[MetricComparison, ...] = ()
    group_comparisons: tuple[GroupComparison, ...] = ()
    insights: tuple[AnalysisInsight, ...] = ()
    warnings: tuple[str, ...] = ()

    @classmethod
    def from_domain(
        cls,
        result: ComparisonResult,
        *,
        options: AnalysisOptions,
    ) -> "ComparisonApiResponse":
        """Map a domain comparison result without echoing request metadata."""

        payload = _safe_model_payload(
            result,
            options=options,
            exclude={"metadata"},
        )
        return cls.model_validate(payload)


class AnalysisApiErrorDetail(BaseModel):
    """Stable, safe error envelope for analysis endpoints."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    message: str
    request_id: str
    timestamp: datetime
    details: dict[str, Any] = Field(default_factory=dict)


class AnalysisApiErrorResponse(BaseModel):
    """Backward-compatible analysis error response."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    detail: str
    error: AnalysisApiErrorDetail
