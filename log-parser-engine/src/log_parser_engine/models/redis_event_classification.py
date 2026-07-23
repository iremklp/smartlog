from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from log_parser_engine.models.enums import LogSeverity


class RedisEventClassification(BaseModel):
    """Immutable event classification for a parsed Redis log line."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    category: str
    event_type: str
    severity: LogSeverity
    summary: str
    matched_rule: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("category must not be empty")
        return cleaned

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("event_type must not be empty")
        return cleaned

    @field_validator("summary")
    @classmethod
    def validate_summary(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("summary must not be empty")
        return cleaned

    @field_validator("attributes")
    @classmethod
    def validate_attributes(cls, value: dict[str, Any]) -> dict[str, Any]:
        return dict(value)

    @property
    def classified(self) -> bool:
        return self.category != "generic" or self.matched_rule is not None
