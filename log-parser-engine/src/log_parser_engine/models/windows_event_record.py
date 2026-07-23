from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WindowsEventRecord(BaseModel):
    """Immutable parsed representation of a Windows Event XML payload."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: int
    timestamp: datetime
    provider_name: str | None = None
    channel: str | None = None
    computer: str | None = None
    level: int | None = None
    task: int | None = None
    opcode: int | None = None
    keywords: str | None = None
    record_id: int | None = None
    execution_process_id: int | None = None
    execution_thread_id: int | None = None
    version: int | None = None
    message: str = ""
    raw_xml: str = ""
    line_number: int | None = None
    event_data: dict[str, str] = Field(default_factory=dict)
    attributes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, value: int) -> int:
        if value < 1:
            raise ValueError("event_id must be 1 or greater")
        return value

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return value.astimezone(timezone.utc)

    @field_validator("message", "raw_xml")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value must not be empty")
        return cleaned

    @field_validator("line_number")
    @classmethod
    def validate_line_number(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError("line_number must be 1 or greater")
        return value

    @field_validator("event_data")
    @classmethod
    def validate_event_data(cls, value: dict[str, str]) -> dict[str, str]:
        return dict(value)

    @field_validator("attributes")
    @classmethod
    def validate_attributes(cls, value: dict[str, Any]) -> dict[str, Any]:
        return dict(value)