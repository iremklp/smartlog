from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

GroupByField = Literal[
    "severity",
    "source_type",
    "event_type",
    "parser_name",
    "host",
    "service",
    "tag",
    "time_bucket",
]

MetricType = Literal[
    "count",
    "average_duration_ms",
    "sum_duration_ms",
]


class EventAggregationRequest(BaseModel):
    """Define one bounded aggregation over a filtered event snapshot."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    group_by: GroupByField
    metric: MetricType
    time_bucket_seconds: int | None = Field(
        default=None,
        ge=1,
        le=86_400,
    )
    limit: int = Field(default=100, ge=1, le=1_000)

    @model_validator(mode="after")
    def _validate_combination(self) -> EventAggregationRequest:
        if self.group_by == "time_bucket":
            if self.time_bucket_seconds is None:
                raise ValueError(
                    "time_bucket_seconds is required when grouping by "
                    "time_bucket"
                )
        elif self.time_bucket_seconds is not None:
            raise ValueError(
                "time_bucket_seconds can only be set when grouping by "
                "time_bucket"
            )

        if self.group_by == "tag" and self.metric != "count":
            raise ValueError(
                "duration metrics cannot be grouped by tag"
            )
        return self


class AggregationBucket(BaseModel):
    """Represent one deterministic aggregation bucket."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    group_value: str | int
    event_count: int = Field(ge=0)
    metric_value: float | None = Field(default=None, ge=0)
    sample_count: int | None = Field(default=None, ge=0)
    bucket_start_time: datetime | None = None
    bucket_end_time: datetime | None = None

    @model_validator(mode="after")
    def _validate_time_bounds(self) -> AggregationBucket:
        if (self.bucket_start_time is None) != (self.bucket_end_time is None):
            raise ValueError(
                "bucket_start_time and bucket_end_time must be set together"
            )
        if self.bucket_start_time is None or self.bucket_end_time is None:
            return self
        if (
            self.bucket_start_time.tzinfo is None
            or self.bucket_end_time.tzinfo is None
        ):
            raise ValueError("time bucket bounds must be timezone-aware")
        if self.bucket_start_time >= self.bucket_end_time:
            raise ValueError(
                "bucket_start_time must be before bucket_end_time"
            )
        return self


class EventAggregationResult(BaseModel):
    """Represent the aggregation produced for an event query."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    request: EventAggregationRequest
    buckets: tuple[AggregationBucket, ...] = Field(default_factory=tuple)
