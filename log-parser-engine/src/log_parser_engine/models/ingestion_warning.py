from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IngestionWarning(BaseModel):
    """Immutable ingestion warning emitted during source preparation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    message: str
    details: dict[str, object] = Field(default_factory=dict)
    recoverable: bool = True

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if not cleaned or not re.fullmatch(r"[A-Z0-9_]+", cleaned):
            raise ValueError("code must be uppercase snake case")
        return cleaned

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("message must not be empty")
        return cleaned

    @field_validator("details")
    @classmethod
    def validate_details(cls, value: dict[str, object]) -> dict[str, object]:
        return dict(value)