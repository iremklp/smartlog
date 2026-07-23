from __future__ import annotations

from copy import deepcopy
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WebErrorRecord(BaseModel):
    """Represents a parsed error log record."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    vendor: str = "generic"
    raw_line: str
    timestamp: str | None = None
    severity: str | None = None
    pid: str | None = None
    connection_id: str | None = None
    message: str | None = None
    client: str | None = None
    server: str | None = None
    request: str | None = None
    host: str | None = None
    upstream: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("raw_line")
    @classmethod
    def validate_raw_line(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("raw_line must not be empty")
        return cleaned

    @field_validator("vendor")
    @classmethod
    def validate_vendor(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("vendor must not be empty")
        return cleaned

    @field_validator("attributes")
    @classmethod
    def validate_attributes(cls, value: dict[str, Any]) -> dict[str, Any]:
        return deepcopy(value)
