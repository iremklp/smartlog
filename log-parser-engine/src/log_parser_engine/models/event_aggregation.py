
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

GROUP_BY_FIELDS = Literal[
    "severity",
    "source_type",
    "event_type",
    "parser_name",
    "host",
    "service",
    "tag",
    "time_bucket",
]

METRIC_TYPES = Literal[
    "count",
    "average_duration_ms",
    "sum_duration_ms",
]


class EventAggregationRequest(BaseModel):
    """Defines a request for aggregating data from a query result."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    group_by: GROUP_BY_FIELDS
    metric: METRIC_TYPES
    time_bucket_seconds: int | None = Field(default=None)
    limit: int = 100

    @field_validator("time_bucket_seconds")
    @classmethod
    def _validate_time_bucket(cls, value: int | None, values: "dict[str, Any]") -> int | None:
        if values.data.get("group_by") == "time_bucket":
            if value is None or not (1 <= value <= 86400):
                raise ValueError("time_bucket_seconds must be between 1 and 86400 when grouping by time_bucket")
        elif value is not None:
            raise ValueError("time_bucket_seconds can only be set when grouping by time_bucket")
        return value

    @field_validator("metric")
    @classmethod
    def _validate_metric_for_duration(cls, value: str, values: "dict[str, Any]") -> str:
        if "duration" in value and values.data.get("group_by") == "tag":
            # This is a semantic limitation for the first version to keep things simple.
            # Aggregating duration by tags can be complex if an event has multiple tags.
            raise ValueError("Duration metrics (average, sum) cannot be grouped by 'tag'")
        return value

    @field_validator("limit")
    @classmethod
    def _validate_limit(cls, value: int) -> int:
        if not (1 <= value <= 1000):
            raise ValueError("limit must be between 1 and 1000")
        return value


class AggregationBucket(BaseModel):
    """Represents a single bucket in an aggregation result."""
    
    model_config = ConfigDict(frozen=True, extra="forbid")

    group_value: str | int
    event_count: int
    metric_value: float | None = None
    sample_count: int | None = None
    bucket_start_time: str | None = None # ISO 8601 string
    bucket_end_time: str | None = None # ISO 8601 string


class EventAggregationResult(BaseModel):
    """The result of an event aggregation query."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    request: EventAggregationRequest
    buckets: tuple[AggregationBucket, ...]
