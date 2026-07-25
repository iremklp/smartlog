"""Time-bucket analysis result models."""

from __future__ import annotations

import math
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _aware(value: datetime | None, *, field_name: str) -> datetime | None:
    if value is not None and (
        value.tzinfo is None or value.utcoffset() is None
    ):
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


class TimelineBucket(BaseModel):
    """Statistics for one inclusive-start, exclusive-end UTC bucket."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    start: datetime
    end: datetime
    event_count: int = Field(ge=0)
    warning_count: int = Field(default=0, ge=0)
    error_count: int = Field(default=0, ge=0)
    critical_count: int = Field(default=0, ge=0)
    error_rate: float = Field(default=0.0, ge=0, le=1)
    average_duration_ms: float | None = Field(default=None, ge=0)
    p95_duration_ms: float | None = Field(default=None, ge=0)
    status_5xx_count: int = Field(default=0, ge=0)

    @field_validator("start", "end")
    @classmethod
    def _aware_bounds(cls, value: datetime) -> datetime:
        result = _aware(value, field_name="timeline bucket bound")
        if result is None:  # pragma: no cover - input is not optional
            raise ValueError("timeline bucket bound is required")
        return result

    @field_validator("error_rate", "average_duration_ms", "p95_duration_ms")
    @classmethod
    def _finite_values(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("timeline numeric values must be finite")
        return value

    @model_validator(mode="after")
    def _bucket_consistency(self) -> "TimelineBucket":
        if self.start >= self.end:
            raise ValueError("timeline bucket start must be before end")
        for count in (
            self.warning_count,
            self.error_count,
            self.critical_count,
            self.status_5xx_count,
        ):
            if count > self.event_count:
                raise ValueError("timeline sub-count cannot exceed event_count")
        return self


class TimelineResult(BaseModel):
    """A deterministic ordered sequence of analysis time buckets."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    bucket_seconds: int = Field(gt=0)
    start: datetime | None = None
    end: datetime | None = None
    buckets: tuple[TimelineBucket, ...] = ()
    empty_bucket_count: int = Field(default=0, ge=0)
    max_bucket_event_count: int = Field(default=0, ge=0)
    average_bucket_event_count: float = Field(default=0.0, ge=0)
    peak_bucket_start: datetime | None = None
    warnings: tuple[str, ...] = ()

    @field_validator("start", "end", "peak_bucket_start")
    @classmethod
    def _aware_times(cls, value: datetime | None) -> datetime | None:
        return _aware(value, field_name="timeline timestamp")

    @field_validator("average_bucket_event_count")
    @classmethod
    def _finite_average(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("average_bucket_event_count must be finite")
        return value

    @field_validator("warnings")
    @classmethod
    def _warnings(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(item.strip() for item in value if item.strip())
        )

    @model_validator(mode="after")
    def _timeline_consistency(self) -> "TimelineResult":
        if self.buckets:
            if self.start is None or self.end is None:
                raise ValueError("non-empty timelines require start and end")
            if self.start >= self.end:
                raise ValueError("timeline start must be before end")
            if any(
                current.start < previous.end
                for previous, current in zip(self.buckets, self.buckets[1:])
            ):
                raise ValueError("timeline buckets must be ordered and non-overlapping")
            if self.buckets[0].start < self.start or self.buckets[-1].end > self.end:
                raise ValueError("timeline buckets must remain within result bounds")
        elif self.start is not None or self.end is not None:
            if self.start is None or self.end is None or self.start > self.end:
                raise ValueError("empty timeline bounds must be valid and paired")
        if self.empty_bucket_count != sum(
            bucket.event_count == 0 for bucket in self.buckets
        ):
            raise ValueError("empty_bucket_count does not match buckets")
        actual_max = max((bucket.event_count for bucket in self.buckets), default=0)
        if self.max_bucket_event_count != actual_max:
            raise ValueError("max_bucket_event_count does not match buckets")
        if self.peak_bucket_start is not None and all(
            bucket.start != self.peak_bucket_start for bucket in self.buckets
        ):
            raise ValueError("peak_bucket_start must identify a returned bucket")
        return self
