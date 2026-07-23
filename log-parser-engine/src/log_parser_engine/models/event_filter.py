
from __future__ import annotations

from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from .enums import LogSeverity, LogSourceType


class EventFilter(BaseModel):
    """Immutable model for defining event filtering criteria."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_ids: tuple[str, ...] = Field(default_factory=tuple)
    exclude_event_ids: tuple[str, ...] = Field(default_factory=tuple)

    start_time: datetime | None = Field(default=None, description="Inclusive start time (UTC).")
    end_time: datetime | None = Field(default=None, description="Exclusive end time (UTC).")

    severities: tuple[LogSeverity, ...] = Field(default_factory=tuple)
    source_types: tuple[LogSourceType, ...] = Field(default_factory=tuple)
    event_types: tuple[str, ...] = Field(default_factory=tuple)
    parser_names: tuple[str, ...] = Field(default_factory=tuple)
    hosts: tuple[str, ...] = Field(default_factory=tuple)
    services: tuple[str, ...] = Field(default_factory=tuple)

    tags_any: tuple[str, ...] = Field(default_factory=tuple, description="Event must have at least one of these tags.")
    tags_all: tuple[str, ...] = Field(default_factory=tuple, description="Event must have all of these tags.")

    message_contains: str | None = Field(default=None, max_length=512)
    message_case_sensitive: bool = False

    client_ips: tuple[str, ...] = Field(default_factory=tuple)
    user_ids: tuple[str, ...] = Field(default_factory=tuple)
    correlation_ids: tuple[str, ...] = Field(default_factory=tuple)

    attribute_exists: tuple[str, ...] = Field(default_factory=tuple, description="Dot-notation paths that must exist.")
    attribute_equals: dict[str, str | int | float | bool | None] = Field(default_factory=dict)

    @field_validator(
        "event_ids",
        "exclude_event_ids",
        "event_types",
        "parser_names",
        "hosts",
        "services",
        "tags_any",
        "tags_all",
        "client_ips",
        "user_ids",
        "correlation_ids",
        "attribute_exists",
    )
    @classmethod
    def _normalize_string_tuple(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            return tuple()
        return tuple(sorted(list(set(item.strip() for item in value if item.strip()))))
    
    @field_validator("attribute_equals")
    @classmethod
    def _normalize_attribute_equals(cls, value: dict) -> dict:
        if not value:
            return {}
        return {k.strip(): v for k, v in value.items() if k.strip()}

    @model_validator(mode="after")
    def _validate_time_range_and_tz(self) -> "EventFilter":
        if self.start_time and self.start_time.tzinfo is None:
            raise ValueError("start_time must be timezone-aware")
        if self.end_time and self.end_time.tzinfo is None:
            raise ValueError("end_time must be timezone-aware")

        if self.start_time and self.end_time and self.start_time > self.end_time:
            raise ValueError("start_time cannot be after end_time")
        
        return self
