from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SyslogRecord(BaseModel):
    """Immutable parsed representation of a syslog message."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    raw_message: str
    priority: int
    facility: int
    severity_code: int
    version: int | None = None
    timestamp: datetime
    host: str | None = None
    application: str | None = None
    process_id: str | None = None
    message_id: str | None = None
    structured_data: str | None = None
    message: str = ""
    line_number: int | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    raw_header: str | None = None
    timestamp_source: str = "syslog"

    @field_validator("raw_message", "message")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value must not be empty")
        return cleaned

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: int) -> int:
        if value < 0 or value > 191:
            raise ValueError("priority must be between 0 and 191")
        return value

    @field_validator("facility")
    @classmethod
    def validate_facility(cls, value: int) -> int:
        if value < 0 or value > 23:
            raise ValueError("facility must be between 0 and 23")
        return value

    @field_validator("severity_code")
    @classmethod
    def validate_severity_code(cls, value: int) -> int:
        if value < 0 or value > 7:
            raise ValueError("severity_code must be between 0 and 7")
        return value

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return value.astimezone(timezone.utc)

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError("version must be 1 or greater")
        return value

    @field_validator("line_number")
    @classmethod
    def validate_line_number(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError("line_number must be 1 or greater")
        return value

    @field_validator("attributes")
    @classmethod
    def validate_attributes(cls, value: dict[str, Any]) -> dict[str, Any]:
        return dict(value)