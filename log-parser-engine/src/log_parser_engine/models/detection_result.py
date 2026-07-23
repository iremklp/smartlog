from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DetectionResult(BaseModel):
    """Represents how strongly a parser matched a given log input."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    matched: bool
    confidence: float
    parser_name: str
    reason: str | None = None
    signals: tuple[str, ...] = Field(default_factory=tuple)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return value

    @field_validator("parser_name")
    @classmethod
    def validate_parser_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("parser_name must not be empty")
        return cleaned

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
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

    @model_validator(mode="after")
    def validate_rules(self) -> "DetectionResult":
        if self.matched and self.confidence <= 0.0:
            raise ValueError("matched results must have confidence greater than 0.0")
        if not self.matched and self.confidence > 0.5:
            raise ValueError(
                "unmatched results must not have confidence greater than 0.5"
            )
        return self

    @classmethod
    def match(
        cls,
        parser_name: str,
        confidence: float,
        *,
        reason: str | None = None,
        signals: tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
    ) -> "DetectionResult":
        return cls(
            matched=True,
            confidence=confidence,
            parser_name=parser_name,
            reason=reason,
            signals=signals,
            metadata=metadata or {},
        )

    @classmethod
    def no_match(
        cls,
        parser_name: str,
        *,
        confidence: float = 0.0,
        reason: str | None = None,
        signals: tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
    ) -> "DetectionResult":
        return cls(
            matched=False,
            confidence=confidence,
            parser_name=parser_name,
            reason=reason,
            signals=signals,
            metadata=metadata or {},
        )
