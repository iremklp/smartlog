from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .event_filter import EventFilter

SAFE_GROUPS = {
    "severity", "source_type", "event_type", "parser_name", "parser",
    "service", "host", "tags", "tag", "http_method", "method",
    "http_status", "status_code", "status_class", "endpoint",
}


def _safe_path(value: str) -> str:
    cleaned = value.strip()
    parts = cleaned.split(".")
    if (
        not cleaned or len(parts) > 20 or any(
            not part or part.startswith("__") or not part.replace("_", "").isalnum()
            for part in parts
        )
    ):
        raise ValueError("unsafe field path")
    return cleaned


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    filter: EventFilter | None = None
    time_bucket_seconds: int | None = None
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
        "severity", "source_type", "event_type", "parser_name", "service", "host",
    )
    percentiles: tuple[float, ...] = (50, 75, 90, 95, 99)
    duration_field: str | None = None
    status_field: str | None = None
    method_field: str | None = None
    path_field: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("time_bucket_seconds")
    @classmethod
    def bucket_positive(cls, value: int | None) -> int | None:
        if value is not None and value <= 0:
            raise ValueError("time_bucket_seconds must be positive")
        return value

    @field_validator("percentiles")
    @classmethod
    def percentile_values(cls, value: tuple[float, ...]) -> tuple[float, ...]:
        unique = tuple(dict.fromkeys(float(item) for item in value))
        if any(item < 0 or item > 100 for item in unique):
            raise ValueError("percentiles must be between 0 and 100")
        return unique

    @field_validator("group_fields")
    @classmethod
    def group_paths(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(_safe_path(item) for item in value))

    @field_validator("duration_field", "status_field", "method_field", "path_field")
    @classmethod
    def optional_paths(cls, value: str | None) -> str | None:
        return _safe_path(value) if value is not None else None

    @field_validator("metadata")
    @classmethod
    def safe_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        encoded = json.dumps(value, allow_nan=False)
        if len(encoded) > 16_384:
            raise ValueError("metadata is too large")
        return value.copy()

    @model_validator(mode="after")
    def request_rules(self) -> "AnalysisRequest":
        for item in (self.start_time, self.end_time):
            if item is not None and item.tzinfo is None:
                raise ValueError("analysis datetimes must be timezone-aware")
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        flags = (
            self.include_summary, self.include_timeline, self.include_distributions,
            self.include_latency, self.include_http, self.include_insights,
            self.include_samples,
        )
        if not any(flags):
            raise ValueError("at least one include flag must be true")
        return self


COMPARISON_METRICS = {
    "event_count", "error_rate", "critical_rate", "average_duration_ms",
    "p50_duration_ms", "p95_duration_ms", "p99_duration_ms",
    "server_error_rate", "client_error_rate", "throughput",
}


class ComparisonRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    baseline_filter: EventFilter | None = None
    comparison_filter: EventFilter | None = None
    baseline_label: str = "Baseline"
    comparison_label: str = "Comparison"
    metrics: tuple[str, ...] = ("event_count", "error_rate", "p95_duration_ms")
    group_by: tuple[str, ...] = ("severity", "event_type", "service")
    top_n: int = Field(default=10, ge=1, le=100)
    minimum_group_count: int = Field(default=1, ge=1)
    include_new_groups: bool = True
    include_disappeared_groups: bool = True
    normalize_by_time_span: bool = True
    significant_change_percent: float | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("baseline_label", "comparison_label")
    @classmethod
    def labels(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned or len(cleaned) > 100:
            raise ValueError("label must be 1-100 characters")
        return cleaned

    @field_validator("metrics")
    @classmethod
    def metric_names(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        result = tuple(dict.fromkeys(value))
        if any(item not in COMPARISON_METRICS for item in result):
            raise ValueError("unsupported comparison metric")
        return result

    @field_validator("group_by")
    @classmethod
    def groups(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        result = tuple(dict.fromkeys(value))
        if any(item not in SAFE_GROUPS for item in result):
            raise ValueError("unsupported comparison group")
        return result

    @model_validator(mode="after")
    def non_empty(self) -> "ComparisonRequest":
        if not self.metrics and not self.group_by:
            raise ValueError("at least one metric or group is required")
        json.dumps(self.metadata, allow_nan=False)
        return self
