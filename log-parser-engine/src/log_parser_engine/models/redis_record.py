from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RedisLogRecord(BaseModel):
    """Immutable parsed representation of a Redis server log line."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp: datetime
    pid: int | None = None
    role_code: str | None = None
    role: str | None = None
    level_marker: str
    message: str
    raw_line: str
    outer_timestamp: datetime | None = None
    outer_host: str | None = None
    outer_process: str | None = None
    line_number: int | None = None
    attributes: dict[str, object] = Field(default_factory=dict)
    timestamp_source: str = "redis"

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return value.astimezone(timezone.utc)

    @field_validator("outer_timestamp")
    @classmethod
    def validate_outer_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("outer_timestamp must be timezone-aware")
        return value.astimezone(timezone.utc) if value is not None else None

    @field_validator("pid")
    @classmethod
    def validate_pid(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError("pid must be 1 or greater")
        return value

    @field_validator("role_code")
    @classmethod
    def validate_role_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().upper()
        if not cleaned:
            return None
        return cleaned

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        return cleaned or None

    @field_validator("level_marker")
    @classmethod
    def validate_level_marker(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned not in {".", "-", "*", "#"}:
            raise ValueError("invalid level marker")
        return cleaned

    @field_validator("message", "raw_line")
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

    @field_validator("attributes")
    @classmethod
    def validate_attributes(cls, value: dict[str, object]) -> dict[str, object]:
        return dict(value)

    @model_validator(mode="after")
    def validate_role_consistency(self) -> "RedisLogRecord":
        if self.role_code is None:
            return self
        if self.role is None:
            raise ValueError("role must be set when role_code is present")
        return self

    @property
    def process_identifier(self) -> str | None:
        if self.pid is not None and self.role_code is not None:
            return f"{self.pid}:{self.role_code}"
        if self.pid is not None:
            return str(self.pid)
        return None
