"""Immutable request models for statistical analysis operations."""

from __future__ import annotations

import json
import math
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .event_filter import EventFilter
from .immutable import FrozenDict, freeze_mapping

SAFE_GROUPS = frozenset(
    {
        "severity",
        "source_type",
        "event_type",
        "parser_name",
        "parser",
        "service",
        "host",
        "tags",
        "tag",
        "http_method",
        "method",
        "http_status",
        "status_code",
        "status_class",
        "endpoint",
    }
)

COMPARISON_GROUPS = frozenset(
    {
        "endpoint",
        "event_type",
        "host",
        "http_status",
        "parser",
        "parser_name",
        "service",
        "severity",
        "status_code",
    }
)

COMPARISON_METRICS = frozenset(
    {
        "event_count",
        "error_rate",
        "critical_rate",
        "average_duration_ms",
        "p50_duration_ms",
        "p95_duration_ms",
        "p99_duration_ms",
        "server_error_rate",
        "client_error_rate",
        "throughput",
    }
)

_MAX_PATH_LENGTH = 256
_MAX_PATH_DEPTH = 10
_MAX_METADATA_BYTES = 16_384
_MAX_METADATA_DEPTH = 5
_MAX_METADATA_KEYS = 100
_MAX_GROUP_FIELDS = 20
_MAX_PERCENTILES = 20
_MAX_TIME_BUCKET_SECONDS = 31_536_000

_SENSITIVE_FIELD_SEGMENTS = frozenset(
    {
        "api_key",
        "apikey",
        "auth",
        "authorization",
        "client_ip",
        "cookie",
        "correlation_id",
        "credential",
        "credentials",
        "message",
        "password",
        "passwd",
        "raw_message",
        "secret",
        "server_ip",
        "session",
        "session_id",
        "set_cookie",
        "source",
        "token",
        "trace_id",
        "user_id",
    }
)

_DURATION_FIELD_LEAVES = frozenset(
    {
        "duration_ms",
        "duration_us",
        "elapsed_ms",
        "latency_ms",
        "latency_us",
        "request_time",
        "request_time_ms",
        "response_time_ms",
        "time_taken_ms",
    }
)
_STATUS_FIELD_LEAVES = frozenset(
    {"http_status", "sc_status", "status", "status_code"}
)
_METHOD_FIELD_LEAVES = frozenset(
    {"cs_method", "http_method", "method"}
)
_PATH_FIELD_LEAVES = frozenset(
    {
        "cs_uri_stem",
        "http_path",
        "path",
        "request_path",
        "route",
        "route_template",
        "uri",
    }
)


def _safe_path(value: str) -> str:
    """Normalize a canonical field or a safe dotted attribute path."""

    cleaned = value.strip()
    parts = cleaned.split(".")
    if (
        not cleaned
        or len(cleaned) > _MAX_PATH_LENGTH
        or len(parts) > _MAX_PATH_DEPTH
        or any(
            not part
            or part.startswith("__")
            or not part.replace("_", "").replace("-", "").isalnum()
            for part in parts
        )
    ):
        raise ValueError("unsafe field path")
    return cleaned


def _validate_json_value(value: object, *, depth: int = 0) -> None:
    if depth > _MAX_METADATA_DEPTH:
        raise ValueError("metadata nesting is too deep")
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("metadata numeric values must be finite")
        return
    if isinstance(value, list):
        for item in value:
            _validate_json_value(item, depth=depth + 1)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or not key or key.startswith("__"):
                raise ValueError("metadata keys must be safe non-empty strings")
            _validate_json_value(item, depth=depth + 1)
        return
    raise ValueError("metadata must contain JSON-safe values")


def _safe_metadata(value: dict[str, Any]) -> dict[str, Any]:
    if len(value) > _MAX_METADATA_KEYS:
        raise ValueError("metadata contains too many keys")
    _validate_json_value(value)
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    if len(encoded.encode("utf-8")) > _MAX_METADATA_BYTES:
        raise ValueError("metadata is too large")
    # JSON round-tripping also gives the immutable model an isolated nested copy.
    copied = json.loads(encoded)
    if not isinstance(copied, dict):  # pragma: no cover - guarded by the input type
        raise ValueError("metadata must be an object")
    return freeze_mapping(copied)


def _normalize_unique_paths(values: tuple[str, ...]) -> tuple[str, ...]:
    if len(values) > _MAX_GROUP_FIELDS:
        raise ValueError(
            f"group_fields cannot contain more than {_MAX_GROUP_FIELDS} items"
        )
    normalized = tuple(dict.fromkeys(_safe_group_path(item) for item in values))
    if len(normalized) > _MAX_GROUP_FIELDS:
        raise ValueError(
            f"group_fields cannot contain more than {_MAX_GROUP_FIELDS} items"
        )
    return normalized


def _safe_group_path(value: str) -> str:
    cleaned = _safe_path(value)
    if cleaned in SAFE_GROUPS:
        return cleaned
    if any(
        segment.casefold().replace("-", "_") in _SENSITIVE_FIELD_SEGMENTS
        for segment in cleaned.split(".")
    ):
        raise ValueError("sensitive fields cannot be used as analysis groups")
    return cleaned


def _purpose_path(
    value: str,
    *,
    allowed_leaves: frozenset[str],
    purpose: str,
) -> str:
    cleaned = _safe_path(value)
    segments = tuple(
        segment.casefold().replace("-", "_")
        for segment in cleaned.split(".")
    )
    if any(segment in _SENSITIVE_FIELD_SEGMENTS for segment in segments):
        raise ValueError(f"sensitive fields cannot be used as {purpose} fields")
    if segments[-1] not in allowed_leaves:
        raise ValueError(f"unsupported {purpose} field")
    return cleaned


class AnalysisRequest(BaseModel):
    """Selects the modules and bounded parameters for one analysis execution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    filter: EventFilter | None = None
    time_bucket_seconds: int | None = Field(
        default=None,
        ge=1,
        le=_MAX_TIME_BUCKET_SECONDS,
    )
    top_n: int | None = Field(default=None, ge=1, le=100)
    include_summary: bool = True
    include_timeline: bool = True
    include_distributions: bool = True
    include_latency: bool = True
    include_http: bool = True
    include_insights: bool = True
    include_samples: bool = False
    sample_size: int = Field(default=10, ge=1, le=100)
    group_fields: tuple[str, ...] = (
        "severity",
        "source_type",
        "event_type",
        "parser_name",
        "service",
        "host",
    )
    percentiles: tuple[float, ...] = (50.0, 75.0, 90.0, 95.0, 99.0)
    duration_field: str | None = None
    status_field: str | None = None
    method_field: str | None = None
    path_field: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=FrozenDict)

    @field_validator("percentiles")
    @classmethod
    def _percentile_values(
        cls,
        value: tuple[float, ...],
    ) -> tuple[float, ...]:
        if len(value) > _MAX_PERCENTILES:
            raise ValueError(
                f"percentiles cannot contain more than {_MAX_PERCENTILES} items"
            )
        unique = tuple(dict.fromkeys(float(item) for item in value))
        if not unique:
            raise ValueError("percentiles must not be empty")
        if any(not math.isfinite(item) or item < 0 or item > 100 for item in unique):
            raise ValueError("percentiles must be finite values between 0 and 100")
        return unique

    @field_validator("group_fields")
    @classmethod
    def _group_paths(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _normalize_unique_paths(value)

    @field_validator("duration_field")
    @classmethod
    def _duration_path(cls, value: str | None) -> str | None:
        return (
            _purpose_path(
                value,
                allowed_leaves=_DURATION_FIELD_LEAVES,
                purpose="duration",
            )
            if value is not None
            else None
        )

    @field_validator("status_field")
    @classmethod
    def _status_path(cls, value: str | None) -> str | None:
        return (
            _purpose_path(
                value,
                allowed_leaves=_STATUS_FIELD_LEAVES,
                purpose="HTTP status",
            )
            if value is not None
            else None
        )

    @field_validator("method_field")
    @classmethod
    def _method_path(cls, value: str | None) -> str | None:
        return (
            _purpose_path(
                value,
                allowed_leaves=_METHOD_FIELD_LEAVES,
                purpose="HTTP method",
            )
            if value is not None
            else None
        )

    @field_validator("path_field")
    @classmethod
    def _path_path(cls, value: str | None) -> str | None:
        return (
            _purpose_path(
                value,
                allowed_leaves=_PATH_FIELD_LEAVES,
                purpose="HTTP path",
            )
            if value is not None
            else None
        )

    @field_validator("metadata")
    @classmethod
    def _metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _safe_metadata(value)

    @model_validator(mode="after")
    def _request_rules(self) -> "AnalysisRequest":
        for item in (self.start_time, self.end_time):
            if item is not None and (
                item.tzinfo is None or item.utcoffset() is None
            ):
                raise ValueError("analysis datetimes must be timezone-aware")
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        flags = (
            self.include_summary,
            self.include_timeline,
            self.include_distributions,
            self.include_latency,
            self.include_http,
            self.include_insights,
            self.include_samples,
        )
        if not any(flags):
            raise ValueError("at least one include flag must be true")
        return self


class ComparisonRequest(BaseModel):
    """Defines two filtered datasets and their bounded comparison dimensions."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    baseline_filter: EventFilter | None = None
    comparison_filter: EventFilter | None = None
    baseline_label: str = "Baseline"
    comparison_label: str = "Comparison"
    metrics: tuple[str, ...] = (
        "event_count",
        "error_rate",
        "p95_duration_ms",
    )
    group_by: tuple[str, ...] = ("severity", "event_type", "service")
    top_n: int = Field(default=10, ge=1, le=100)
    minimum_group_count: int = Field(default=1, ge=1)
    include_new_groups: bool = True
    include_disappeared_groups: bool = True
    normalize_by_time_span: bool = True
    significant_change_percent: float | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=FrozenDict)

    @field_validator("baseline_label", "comparison_label")
    @classmethod
    def _labels(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned or len(cleaned) > 100:
            raise ValueError("label must be 1-100 characters")
        return cleaned

    @field_validator("metrics")
    @classmethod
    def _metric_names(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        result = tuple(dict.fromkeys(item.strip() for item in value))
        if any(item not in COMPARISON_METRICS for item in result):
            raise ValueError("unsupported comparison metric")
        return result

    @field_validator("group_by")
    @classmethod
    def _groups(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        result = tuple(dict.fromkeys(item.strip() for item in value))
        if any(item not in COMPARISON_GROUPS for item in result):
            raise ValueError("unsupported comparison group")
        return result

    @field_validator("significant_change_percent")
    @classmethod
    def _finite_threshold(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("significant_change_percent must be finite")
        return value

    @field_validator("metadata")
    @classmethod
    def _metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _safe_metadata(value)

    @model_validator(mode="after")
    def _non_empty(self) -> "ComparisonRequest":
        if not self.metrics and not self.group_by:
            raise ValueError("at least one metric or group is required")
        return self
