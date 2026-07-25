"""High-level statistical summary model."""

from __future__ import annotations

import math
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AnalysisSummary(BaseModel):
    """Exact counters and rates for the filtered event snapshot.

    ``error_rate`` is ``(error_count + critical_count) / matched_event_count``.
    It deliberately does not represent HTTP success semantics.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    input_event_count: int = Field(ge=0)
    matched_event_count: int = Field(ge=0)
    trace_count: int = Field(default=0, ge=0)
    debug_count: int = Field(default=0, ge=0)
    info_count: int = Field(default=0, ge=0)
    warning_count: int = Field(default=0, ge=0)
    error_count: int = Field(default=0, ge=0)
    critical_count: int = Field(default=0, ge=0)
    unknown_count: int = Field(default=0, ge=0)
    error_or_critical_count: int = Field(default=0, ge=0)
    error_rate: float = Field(default=0.0, ge=0, le=1)
    critical_rate: float = Field(default=0.0, ge=0, le=1)
    unique_event_type_count: int = Field(default=0, ge=0)
    unique_service_count: int = Field(default=0, ge=0)
    unique_host_count: int = Field(default=0, ge=0)
    unique_parser_count: int = Field(default=0, ge=0)
    unique_source_type_count: int = Field(default=0, ge=0)
    earliest_timestamp: datetime | None = None
    latest_timestamp: datetime | None = None
    time_span_seconds: float | None = Field(default=None, ge=0)
    events_per_second: float | None = Field(default=None, ge=0)
    events_per_minute: float | None = Field(default=None, ge=0)
    events_with_duration: int = Field(default=0, ge=0)
    events_with_http_status: int = Field(default=0, ge=0)
    duplicate_content_count: int = Field(default=0, ge=0)
    out_of_order_timestamp_count: int = Field(default=0, ge=0)

    @field_validator("earliest_timestamp", "latest_timestamp")
    @classmethod
    def _aware_datetime(cls, value: datetime | None) -> datetime | None:
        if value is not None and (
            value.tzinfo is None or value.utcoffset() is None
        ):
            raise ValueError("summary timestamps must be timezone-aware")
        return value

    @field_validator(
        "error_rate",
        "critical_rate",
        "time_span_seconds",
        "events_per_second",
        "events_per_minute",
    )
    @classmethod
    def _finite_values(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("summary numeric values must be finite")
        return value

    @model_validator(mode="after")
    def _consistent_summary(self) -> "AnalysisSummary":
        if self.matched_event_count > self.input_event_count:
            raise ValueError("matched_event_count cannot exceed input_event_count")
        if self.error_or_critical_count != self.error_count + self.critical_count:
            raise ValueError(
                "error_or_critical_count must equal error_count plus critical_count"
            )
        if self.error_or_critical_count > self.matched_event_count:
            raise ValueError("severity counts cannot exceed matched_event_count")
        if self.events_with_duration > self.matched_event_count:
            raise ValueError("events_with_duration cannot exceed matched_event_count")
        if self.events_with_http_status > self.matched_event_count:
            raise ValueError(
                "events_with_http_status cannot exceed matched_event_count"
            )
        if self.earliest_timestamp is None or self.latest_timestamp is None:
            if self.earliest_timestamp is not None or self.latest_timestamp is not None:
                raise ValueError("summary timestamp bounds must be provided together")
        elif self.earliest_timestamp > self.latest_timestamp:
            raise ValueError("earliest_timestamp cannot exceed latest_timestamp")
        return self

    @property
    def non_error_event_count(self) -> int:
        """Return events not classified as error or critical."""

        return self.matched_event_count - self.error_or_critical_count
