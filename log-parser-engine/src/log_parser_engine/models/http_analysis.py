"""HTTP-specific statistical analysis result models."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .distribution import DistributionResult
from .immutable import FrozenDict, freeze_mapping
from .ranked_item import RankedItem
from .timeline import TimelineResult


class HTTPStatusBreakdown(BaseModel):
    """HTTP status class counts for one method or service group."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str
    total_count: int = Field(ge=0)
    informational_count: int = Field(default=0, ge=0)
    success_count: int = Field(default=0, ge=0)
    redirect_count: int = Field(default=0, ge=0)
    client_error_count: int = Field(default=0, ge=0)
    server_error_count: int = Field(default=0, ge=0)
    unknown_status_count: int = Field(default=0, ge=0)
    error_rate: float = Field(default=0.0, ge=0, le=1)

    @field_validator("key")
    @classmethod
    def _key(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("HTTP status group key must not be empty")
        return cleaned

    @field_validator("error_rate")
    @classmethod
    def _finite_rate(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("HTTP error rate must be finite")
        return value

    @model_validator(mode="after")
    def _count_consistency(self) -> "HTTPStatusBreakdown":
        total = (
            self.informational_count
            + self.success_count
            + self.redirect_count
            + self.client_error_count
            + self.server_error_count
            + self.unknown_status_count
        )
        if total != self.total_count:
            raise ValueError("HTTP status class counts must equal total_count")
        return self


class EndpointAnalysis(BaseModel):
    """Request volume, errors, latency, and dimensions for one endpoint."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    endpoint: str
    request_count: int = Field(ge=0)
    percentage: float = Field(ge=0, le=100)
    error_count: int = Field(ge=0)
    error_rate: float = Field(ge=0, le=1)
    client_error_count: int = Field(default=0, ge=0)
    server_error_count: int = Field(default=0, ge=0)
    latency_sample_count: int = Field(default=0, ge=0)
    average_duration_ms: float | None = Field(default=None, ge=0)
    p95_duration_ms: float | None = Field(default=None, ge=0)
    max_duration_ms: float | None = Field(default=None, ge=0)
    methods: tuple[str, ...] = ()
    top_status_codes: tuple[RankedItem, ...] = ()
    services: tuple[str, ...] = ()
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    attributes: dict[str, Any] = Field(default_factory=FrozenDict)

    @field_validator("endpoint")
    @classmethod
    def _endpoint(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("endpoint must not be empty")
        return cleaned

    @field_validator(
        "percentage",
        "error_rate",
        "average_duration_ms",
        "p95_duration_ms",
        "max_duration_ms",
    )
    @classmethod
    def _finite_numbers(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("endpoint numeric values must be finite")
        return value

    @field_validator("methods", "services")
    @classmethod
    def _normalized_values(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(item.strip() for item in value if item.strip())
        )

    @field_validator("first_seen", "last_seen")
    @classmethod
    def _aware_times(cls, value: datetime | None) -> datetime | None:
        if value is not None and (
            value.tzinfo is None or value.utcoffset() is None
        ):
            raise ValueError("endpoint timestamps must be timezone-aware")
        return value

    @field_validator("attributes")
    @classmethod
    def _attributes(cls, value: dict[str, Any]) -> dict[str, Any]:
        return freeze_mapping(value)

    @model_validator(mode="after")
    def _endpoint_consistency(self) -> "EndpointAnalysis":
        if self.error_count > self.request_count:
            raise ValueError("endpoint error_count cannot exceed request_count")
        if self.client_error_count + self.server_error_count != self.error_count:
            raise ValueError(
                "endpoint client and server error counts must equal error_count"
            )
        values = (
            self.average_duration_ms,
            self.p95_duration_ms,
            self.max_duration_ms,
        )
        if self.latency_sample_count == 0 and any(
            value is not None for value in values
        ):
            raise ValueError("endpoint without latency samples cannot have statistics")
        if self.latency_sample_count > 0 and any(
            value is None for value in values
        ):
            raise ValueError("endpoint latency samples require all statistics")
        if self.first_seen is None or self.last_seen is None:
            if self.first_seen is not None or self.last_seen is not None:
                raise ValueError("endpoint time bounds must be provided together")
        elif self.first_seen > self.last_seen:
            raise ValueError("endpoint first_seen cannot exceed last_seen")
        return self


class HTTPAnalysis(BaseModel):
    """HTTP coverage, status rates, distributions, endpoint rankings and trend."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    http_event_count: int = Field(ge=0)
    events_with_status: int = Field(ge=0)
    events_with_method: int = Field(ge=0)
    events_with_path: int = Field(ge=0)
    informational_count: int = Field(default=0, ge=0)
    success_count: int = Field(default=0, ge=0)
    redirect_count: int = Field(default=0, ge=0)
    non_error_count: int = Field(default=0, ge=0)
    client_error_count: int = Field(default=0, ge=0)
    server_error_count: int = Field(default=0, ge=0)
    unknown_status_count: int = Field(default=0, ge=0)
    success_rate: float = Field(default=0.0, ge=0, le=1)
    non_error_rate: float = Field(default=0.0, ge=0, le=1)
    client_error_rate: float = Field(default=0.0, ge=0, le=1)
    server_error_rate: float = Field(default=0.0, ge=0, le=1)
    total_error_rate: float = Field(default=0.0, ge=0, le=1)
    status_class_distribution: DistributionResult
    status_code_distribution: DistributionResult
    method_distribution: DistributionResult
    endpoint_distribution: DistributionResult
    slowest_endpoints: tuple[EndpointAnalysis, ...] = ()
    highest_error_endpoints: tuple[EndpointAnalysis, ...] = ()
    status_by_method: tuple[HTTPStatusBreakdown, ...] = ()
    status_by_service: tuple[HTTPStatusBreakdown, ...] = ()
    timeline: TimelineResult | None = None
    warnings: tuple[str, ...] = ()

    @field_validator(
        "success_rate",
        "non_error_rate",
        "client_error_rate",
        "server_error_rate",
        "total_error_rate",
    )
    @classmethod
    def _finite_rates(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("HTTP rates must be finite")
        return value

    @field_validator("warnings")
    @classmethod
    def _warnings(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(item.strip() for item in value if item.strip())
        )

    @model_validator(mode="after")
    def _http_consistency(self) -> "HTTPAnalysis":
        if any(
            count > self.http_event_count
            for count in (
                self.events_with_status,
                self.events_with_method,
                self.events_with_path,
                self.unknown_status_count,
            )
        ):
            raise ValueError("HTTP coverage counts cannot exceed http_event_count")
        valid_statuses = (
            self.informational_count
            + self.success_count
            + self.redirect_count
            + self.client_error_count
            + self.server_error_count
        )
        if valid_statuses != self.events_with_status:
            raise ValueError("HTTP status class counts must equal events_with_status")
        if self.non_error_count != (
            self.informational_count + self.success_count + self.redirect_count
        ):
            raise ValueError("non_error_count does not match HTTP status classes")
        if self.events_with_status + self.unknown_status_count != (
            self.http_event_count
        ):
            raise ValueError(
                "known and unknown HTTP status counts must equal http_event_count"
            )
        return self


# The specification uses both spellings. Keep one implementation and expose a
# compatibility alias rather than duplicate domain types.
HttpAnalysis = HTTPAnalysis
