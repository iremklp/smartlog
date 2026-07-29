from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .enums import LogSeverity, LogSourceType
from .immutable import FrozenDict, FrozenList, freeze_mapping


class LogEvent(BaseModel):
    """Immutable domain model for normalized log events."""

    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")

    schema_version: str = Field(default="1.0", min_length=1)
    event_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_type: LogSourceType
    severity: LogSeverity = LogSeverity.UNKNOWN
    event_type: str | None = None
    message: str
    raw_message: str
    service: str | None = None
    application: str | None = None
    environment: str | None = None
    host: str | None = None
    source: str | None = None
    trace_id: str | None = None
    correlation_id: str | None = None
    user_id: str | None = None
    client_ip: str | None = None
    server_ip: str | None = None
    http_method: str | None = None
    http_path: str | None = None
    http_status: int | None = None
    duration_ms: float | None = None
    attributes: dict[str, Any] = Field(default_factory=FrozenDict)
    tags: list[str] = Field(default_factory=FrozenList)

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return value

    @field_validator("message", "raw_message")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value must not be empty")
        return cleaned

    @field_validator("http_status")
    @classmethod
    def validate_http_status(cls, value: int | None) -> int | None:
        if value is not None and not 100 <= value <= 599:
            raise ValueError("http_status must be between 100 and 599")
        return value

    @field_validator("duration_ms")
    @classmethod
    def validate_duration(cls, value: float | None) -> float | None:
        if value is not None and (not math.isfinite(value) or value < 0):
            raise ValueError("duration_ms must be finite and non-negative")
        return value

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for tag in value:
            cleaned = tag.strip()
            if not cleaned:
                continue
            if cleaned not in seen:
                normalized.append(cleaned)
                seen.add(cleaned)
        return FrozenList(normalized)

    @field_validator("attributes")
    @classmethod
    def freeze_attributes(cls, value: dict[str, Any]) -> dict[str, Any]:
        return freeze_mapping(value)

    @model_validator(mode="after")
    def ensure_ingested_is_timezone_aware(self) -> "LogEvent":
        if self.ingested_at.tzinfo is None:
            raise ValueError("ingested_at must be timezone-aware")
        return self

    @field_validator("ingested_at")
    @classmethod
    def normalize_ingested_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def with_validated_updates(
        self,
        updates: Mapping[str, Any],
    ) -> "LogEvent":
        """Return a fully revalidated copy with the supplied field updates.

        Pydantic's ``model_copy(update=...)`` deliberately skips validation.
        Reconstructing from a Python-mode dump ensures validators run again,
        including the recursive freezing of attributes and tags.
        """

        payload = self.model_dump(mode="python")
        payload.update(updates)
        return LogEvent.model_validate(payload)
