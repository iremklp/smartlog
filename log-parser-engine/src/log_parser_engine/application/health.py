from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ApplicationHealth(BaseModel):
    """Health snapshot for the application service."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["healthy", "degraded"]
    created_at: datetime
    checked_at: datetime
    uptime_ms: float
    parser_count: int
    enabled_parser_count: int
    store_event_count: int
    warnings: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("uptime_ms")
    @classmethod
    def validate_uptime(cls, value: float) -> float:
        if value < 0:
            raise ValueError("uptime_ms must not be negative")
        return value

    @field_validator("warnings")
    @classmethod
    def normalize_warnings(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(str(item).strip() for item in value if str(item).strip())