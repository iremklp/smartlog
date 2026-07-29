
from __future__ import annotations

import math
from datetime import datetime
from typing import TypeAlias

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from .enums import LogSeverity, LogSourceType
from .immutable import FrozenDict

FilterScalar: TypeAlias = str | int | float | bool | None

_MAX_VALUES_PER_FILTER = 100
_MAX_TOTAL_FILTER_VALUES = 500
_MAX_ATTRIBUTE_PATH_DEPTH = 10
_MAX_ATTRIBUTE_PATH_LENGTH = 256


class EventFilter(BaseModel):
    """Immutable model for defining event filtering criteria."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_ids: tuple[str, ...] = Field(default_factory=tuple)
    exclude_event_ids: tuple[str, ...] = Field(default_factory=tuple)

    start_time: datetime | None = Field(
        default=None,
        description="Inclusive start time (UTC).",
    )
    end_time: datetime | None = Field(
        default=None,
        description="Exclusive end time (UTC).",
    )

    severities: tuple[LogSeverity, ...] = Field(default_factory=tuple)
    source_types: tuple[LogSourceType, ...] = Field(default_factory=tuple)
    event_types: tuple[str, ...] = Field(default_factory=tuple)
    parser_names: tuple[str, ...] = Field(default_factory=tuple)
    hosts: tuple[str, ...] = Field(default_factory=tuple)
    services: tuple[str, ...] = Field(default_factory=tuple)

    tags_any: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Event must have at least one of these tags.",
    )
    tags_all: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Event must have all of these tags.",
    )

    message_contains: str | None = Field(default=None, max_length=512)
    message_case_sensitive: bool = False

    client_ips: tuple[str, ...] = Field(default_factory=tuple)
    user_ids: tuple[str, ...] = Field(default_factory=tuple)
    correlation_ids: tuple[str, ...] = Field(default_factory=tuple)

    attribute_exists: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Dot-notation paths that must exist.",
    )
    attribute_equals: dict[str, FilterScalar] = Field(default_factory=FrozenDict)

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
        normalized = tuple(
            sorted(set(item.strip() for item in value if item.strip()))
        )
        if len(normalized) > _MAX_VALUES_PER_FILTER:
            raise ValueError("filter contains too many values")
        return normalized

    @field_validator("attribute_equals")
    @classmethod
    def _normalize_attribute_equals(
        cls,
        value: dict[str, FilterScalar],
    ) -> dict[str, FilterScalar]:
        if not value:
            return FrozenDict()
        normalized: dict[str, FilterScalar] = {}
        for raw_path, item in value.items():
            path = cls._safe_attribute_path(raw_path)
            if isinstance(item, float) and not math.isfinite(item):
                raise ValueError("attribute filter numbers must be finite")
            normalized[path] = item
        if len(normalized) > _MAX_VALUES_PER_FILTER:
            raise ValueError("filter contains too many attribute comparisons")
        return FrozenDict(normalized)

    @field_validator("attribute_exists")
    @classmethod
    def _normalize_attribute_paths(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        normalized = tuple(
            sorted(
                {
                    cls._safe_attribute_path(path)
                    for path in value
                    if path.strip()
                }
            )
        )
        if len(normalized) > _MAX_VALUES_PER_FILTER:
            raise ValueError("filter contains too many attribute paths")
        return normalized

    @staticmethod
    def _safe_attribute_path(value: str) -> str:
        cleaned = value.strip()
        parts = cleaned.split(".")
        if (
            not cleaned
            or len(cleaned) > _MAX_ATTRIBUTE_PATH_LENGTH
            or len(parts) > _MAX_ATTRIBUTE_PATH_DEPTH
            or any(
                not part
                or part.startswith("__")
                or not part.replace("_", "").replace("-", "").isalnum()
                for part in parts
            )
        ):
            raise ValueError("unsafe attribute filter path")
        return cleaned

    @model_validator(mode="after")
    def _validate_time_range_and_tz(self) -> "EventFilter":
        if (
            self.start_time
            and (
                self.start_time.tzinfo is None
                or self.start_time.utcoffset() is None
            )
        ):
            raise ValueError("start_time must be timezone-aware")
        if (
            self.end_time
            and (
                self.end_time.tzinfo is None
                or self.end_time.utcoffset() is None
            )
        ):
            raise ValueError("end_time must be timezone-aware")

        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValueError("start_time cannot be after end_time")

        total_values = sum(
            len(value)
            for value in (
                self.event_ids,
                self.exclude_event_ids,
                self.severities,
                self.source_types,
                self.event_types,
                self.parser_names,
                self.hosts,
                self.services,
                self.tags_any,
                self.tags_all,
                self.client_ips,
                self.user_ids,
                self.correlation_ids,
                self.attribute_exists,
            )
        ) + len(self.attribute_equals)
        if total_values > _MAX_TOTAL_FILTER_VALUES:
            raise ValueError("filter contains too many total values")

        return self
