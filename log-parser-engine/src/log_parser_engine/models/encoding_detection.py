from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


class EncodingDetection(BaseModel):
    """Immutable encoding detection result."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    encoding: str
    confidence: float
    source: Literal["forced", "bom", "utf8", "detector", "fallback", "text"]
    bom: str | None = None
    is_ascii: bool = False
    alternatives: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    @field_validator("encoding")
    @classmethod
    def validate_encoding(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("encoding must not be empty")
        return cleaned

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return value

    @field_validator("bom")
    @classmethod
    def normalize_bom(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        return cleaned or None

    @field_validator("alternatives", "notes")
    @classmethod
    def normalize_strings(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            cleaned = str(item).strip().lower()
            if not cleaned or cleaned in seen:
                continue
            normalized.append(cleaned)
            seen.add(cleaned)
        return tuple(normalized)

    @property
    def certain(self) -> bool:
        return self.confidence >= 0.9