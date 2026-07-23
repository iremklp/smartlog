from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .enums import LogSourceType


class DetectionCandidate(BaseModel):
    """A single parser evaluation result used during detection scoring."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    parser_name: str
    parser_version: str
    confidence: float
    matched: bool
    priority: int = Field(default=100)
    reason: str | None = None
    signals: tuple[str, ...] = Field(default_factory=tuple)
    source_type: LogSourceType
    duration_ms: float = Field(default=0.0)
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("parser_name", "parser_version")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value must not be empty")
        return cleaned

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return value

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: int) -> int:
        if not 0 <= value <= 1000:
            raise ValueError("priority must be between 0 and 1000")
        return value

    @field_validator("reason", "error")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("signals")
    @classmethod
    def normalize_signals(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized: list[str] = []
        seen: set[str] = set()
        for signal in value:
            cleaned = str(signal).strip()
            if not cleaned:
                continue
            if cleaned not in seen:
                normalized.append(cleaned)
                seen.add(cleaned)
        return tuple(normalized)

    @field_validator("duration_ms")
    @classmethod
    def validate_duration(cls, value: float) -> float:
        if value < 0:
            raise ValueError("duration_ms must not be negative")
        return value

    @model_validator(mode="after")
    def validate_rules(self) -> "DetectionCandidate":
        if self.matched and self.confidence <= 0.0:
            raise ValueError(
                "matched candidates must have confidence greater than 0.0"
            )
        if not self.matched and self.confidence > 0.5:
            raise ValueError(
                "unmatched candidates must not have confidence greater than 0.5"
            )
        if self.error is not None and self.matched:
            raise ValueError("error candidates cannot be matched")
        if self.error is not None and self.confidence != 0.0:
            raise ValueError("error candidates must have zero confidence")
        return self

    @property
    def identifier(self) -> str:
        return f"{self.parser_name}@{self.parser_version}"
