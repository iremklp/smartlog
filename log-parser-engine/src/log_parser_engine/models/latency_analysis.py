"""Latency analysis result models."""

from __future__ import annotations

import math
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .percentile_summary import PercentileSummary


class LatencyBucket(BaseModel):
    """One non-overlapping latency histogram bucket in milliseconds."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    lower_bound_ms: float | None
    upper_bound_ms: float | None
    count: int = Field(ge=0)
    percentage: float = Field(ge=0, le=100)
    label: str

    @field_validator("lower_bound_ms", "upper_bound_ms", "percentage")
    @classmethod
    def _finite_values(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("latency bucket values must be finite")
        return value

    @field_validator("lower_bound_ms", "upper_bound_ms")
    @classmethod
    def _non_negative_bounds(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("latency bucket bounds must not be negative")
        return value

    @field_validator("label")
    @classmethod
    def _label(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("latency bucket label must not be empty")
        return cleaned

    @model_validator(mode="after")
    def _ordered_bounds(self) -> "LatencyBucket":
        if (
            self.lower_bound_ms is not None
            and self.upper_bound_ms is not None
            and self.lower_bound_ms >= self.upper_bound_ms
        ):
            raise ValueError("latency bucket lower bound must be below upper bound")
        return self


class SlowEvent(BaseModel):
    """Safe summary of a high-latency event without raw log content."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str
    timestamp: datetime
    duration_ms: float = Field(ge=0)
    event_type: str | None = None
    service: str | None = None
    host: str | None = None
    path: str | None = None
    message_preview: str | None = Field(default=None, max_length=1_000)

    @field_validator("event_id")
    @classmethod
    def _event_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("event_id must not be empty")
        return cleaned

    @field_validator("timestamp")
    @classmethod
    def _aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("slow event timestamp must be timezone-aware")
        return value

    @field_validator("duration_ms")
    @classmethod
    def _finite_duration(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("duration_ms must be finite")
        return value

    @field_validator("event_type", "service", "host", "path", "message_preview")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class EndpointLatency(BaseModel):
    """Descriptive latency statistics for a service, event type, or endpoint."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str
    sample_count: int = Field(ge=0)
    minimum_ms: float | None = Field(default=None, ge=0)
    maximum_ms: float | None = Field(default=None, ge=0)
    mean_ms: float | None = Field(default=None, ge=0)
    p95_ms: float | None = Field(default=None, ge=0)
    missing_count: int = Field(default=0, ge=0)

    @field_validator("key")
    @classmethod
    def _key(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("latency group key must not be empty")
        return cleaned

    @field_validator("minimum_ms", "maximum_ms", "mean_ms", "p95_ms")
    @classmethod
    def _finite_statistics(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("latency statistics must be finite")
        return value

    @model_validator(mode="after")
    def _statistics_consistency(self) -> "EndpointLatency":
        values = (self.minimum_ms, self.maximum_ms, self.mean_ms, self.p95_ms)
        if self.sample_count == 0 and any(value is not None for value in values):
            raise ValueError("empty latency groups cannot have statistics")
        if self.sample_count > 0 and any(value is None for value in values):
            raise ValueError("sampled latency groups require all statistics")
        if (
            self.minimum_ms is not None
            and self.maximum_ms is not None
            and self.minimum_ms > self.maximum_ms
        ):
            raise ValueError("minimum_ms cannot exceed maximum_ms")
        return self


class LatencyAnalysis(BaseModel):
    """Duration coverage, descriptive statistics, histogram, and rankings."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    detected_field: str | None = None
    unit: str = "ms"
    total_events: int = Field(ge=0)
    sample_count: int = Field(ge=0)
    missing_count: int = Field(ge=0)
    invalid_count: int = Field(ge=0)
    minimum_ms: float | None = Field(default=None, ge=0)
    maximum_ms: float | None = Field(default=None, ge=0)
    mean_ms: float | None = Field(default=None, ge=0)
    median_ms: float | None = Field(default=None, ge=0)
    standard_deviation_ms: float | None = Field(default=None, ge=0)
    percentiles: PercentileSummary
    slowest_events: tuple[SlowEvent, ...] = ()
    latency_buckets: tuple[LatencyBucket, ...] = ()
    per_service: tuple[EndpointLatency, ...] = ()
    per_event_type: tuple[EndpointLatency, ...] = ()
    per_endpoint: tuple[EndpointLatency, ...] = ()
    warnings: tuple[str, ...] = ()

    @field_validator("detected_field")
    @classmethod
    def _detected_field(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("unit")
    @classmethod
    def _unit(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("latency unit must not be empty")
        return cleaned

    @field_validator(
        "minimum_ms",
        "maximum_ms",
        "mean_ms",
        "median_ms",
        "standard_deviation_ms",
    )
    @classmethod
    def _finite_statistics(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("latency statistics must be finite")
        return value

    @field_validator("warnings")
    @classmethod
    def _warnings(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(item.strip() for item in value if item.strip())
        )

    @model_validator(mode="after")
    def _analysis_consistency(self) -> "LatencyAnalysis":
        if self.sample_count + self.missing_count + self.invalid_count != (
            self.total_events
        ):
            raise ValueError(
                "sample_count, missing_count, and invalid_count must equal total_events"
            )
        statistics = (
            self.minimum_ms,
            self.maximum_ms,
            self.mean_ms,
            self.median_ms,
            self.standard_deviation_ms,
        )
        if self.sample_count == 0 and any(item is not None for item in statistics):
            raise ValueError("empty latency samples cannot have statistics")
        if self.sample_count > 0 and any(item is None for item in statistics):
            raise ValueError("latency samples require all descriptive statistics")
        if (
            self.minimum_ms is not None
            and self.maximum_ms is not None
            and self.minimum_ms > self.maximum_ms
        ):
            raise ValueError("minimum_ms cannot exceed maximum_ms")
        if self.percentiles.sample_count != self.sample_count:
            raise ValueError(
                "percentile valid sample count must equal latency sample count"
            )
        return self
