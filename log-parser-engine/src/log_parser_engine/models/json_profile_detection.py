from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class JsonProfileDetection(BaseModel):
    """Represents the detected structured logging profile for a JSON object."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    profile: str
    confidence: float = Field(default=0.0)
    signals: tuple[str, ...] = Field(default_factory=tuple)
    matched_paths: tuple[str, ...] = Field(default_factory=tuple)
    reason: str = "unknown"

    @field_validator("profile")
    @classmethod
    def validate_profile(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("profile must not be empty")
        return cleaned

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return value

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("reason must not be empty")
        return cleaned

    @property
    def matched(self) -> bool:
        return self.confidence >= 0.5
