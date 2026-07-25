"""Reusable numeric analysis metric model."""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MetricValue(BaseModel):
    """A numeric metric together with sample quality information."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    value: int | float | None
    unit: str | None = None
    sample_count: int = Field(ge=0)
    missing_count: int = Field(ge=0)
    valid: bool
    notes: tuple[str, ...] = ()

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("metric name must not be empty")
        return cleaned

    @field_validator("unit")
    @classmethod
    def _unit(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("value")
    @classmethod
    def _finite_value(cls, value: int | float | None) -> int | float | None:
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("metric value must be finite")
        return value

    @field_validator("notes")
    @classmethod
    def _notes(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(note.strip() for note in value if note.strip())
        )

    @model_validator(mode="after")
    def _valid_value(self) -> "MetricValue":
        if self.valid and self.value is None:
            raise ValueError("a valid metric must have a value")
        return self
