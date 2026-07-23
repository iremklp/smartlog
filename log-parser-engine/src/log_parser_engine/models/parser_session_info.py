from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ParserSessionInfo(BaseModel):
    """Immutable summary of a parser session in a batch stream."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    parser_name: str
    parser_version: str
    selected_by: Literal["explicit", "detection", "redetection"]
    detection_confidence: float | None = None
    detection_reason: str | None = None
    started_at_record: int
    ended_at_record: int | None = None
    records_attempted: int = 0
    records_succeeded: int = 0
    records_failed: int = 0
    stateful: bool = False
    attributes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("parser_name", "parser_version")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value must not be empty")
        return cleaned

    @field_validator("detection_reason")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator(
        "started_at_record",
        "ended_at_record",
        "records_attempted",
        "records_succeeded",
        "records_failed",
    )
    @classmethod
    def validate_non_negative_counts(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value < 0:
            raise ValueError("count values must not be negative")
        return value

    @field_validator("detection_confidence")
    @classmethod
    def validate_confidence(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if not 0.0 <= value <= 1.0:
            raise ValueError("detection_confidence must be between 0.0 and 1.0")
        return value

    @field_validator("attributes")
    @classmethod
    def copy_attributes(cls, value: dict[str, Any]) -> dict[str, Any]:
        return dict(value)

    @model_validator(mode="after")
    def validate_rules(self) -> "ParserSessionInfo":
        if self.started_at_record < 1:
            raise ValueError("started_at_record must be >= 1")
        if self.ended_at_record is not None and self.ended_at_record < self.started_at_record:
            raise ValueError("ended_at_record must be >= started_at_record")
        if self.records_succeeded + self.records_failed > self.records_attempted:
            raise ValueError("session success/failure counts exceed attempted")
        return self
