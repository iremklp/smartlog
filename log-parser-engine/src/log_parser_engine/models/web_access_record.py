from __future__ import annotations

from copy import deepcopy
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WebAccessRecord(BaseModel):
    """Represents a parsed access log record."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    vendor: str = "generic"
    raw_line: str
    remote_addr: str | None = None
    remote_user: str | None = None
    timestamp: str | None = None
    request: str | None = None
    status_code: int | None = None
    bytes_sent: int | None = None
    http_referer: str | None = None
    http_user_agent: str | None = None
    request_path: str | None = None
    http_method: str | None = None
    http_version: str | None = None
    upstream: str | None = None
    server_name: str | None = None
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
