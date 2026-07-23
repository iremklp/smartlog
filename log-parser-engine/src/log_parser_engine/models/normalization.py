from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import LogSourceType
from .log_event import LogEvent


class NormalizationInput(BaseModel):
    """Input payload for normalization."""

    model_config = ConfigDict(frozen=True)

    data: dict[str, Any] = Field(default_factory=dict)
    source_type: str | LogSourceType | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("source_type")
    @classmethod
    def normalize_source_type(
        cls, value: str | LogSourceType | None
    ) -> str | LogSourceType | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip() or None
        return value


class NormalizationWarning(BaseModel):
    """Non-fatal warning emitted during normalization."""

    model_config = ConfigDict(frozen=True)

    message: str

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("message must not be empty")
        return cleaned


class NormalizationResult(BaseModel):
    """Result of normalizing a payload."""

    model_config = ConfigDict(frozen=True)

    event: LogEvent
    warnings: list[NormalizationWarning] = Field(default_factory=list)

    @field_validator("warnings")
    @classmethod
    def normalize_warnings(
        cls, value: list[NormalizationWarning]
    ) -> list[NormalizationWarning]:
        return value
