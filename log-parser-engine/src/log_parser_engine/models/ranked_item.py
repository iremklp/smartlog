"""Ranked analysis result model."""

from __future__ import annotations

import math
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .immutable import FrozenDict, freeze_mapping


class RankedItem(BaseModel):
    """One deterministically ordered entry in a top-N result."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rank: int = Field(ge=1)
    key: str
    display_value: str
    count: int = Field(ge=0)
    percentage: float = Field(ge=0, le=100)
    metric_value: float | None = None
    metric_unit: str | None = None
    attributes: dict[str, Any] = Field(default_factory=FrozenDict)

    @field_validator("key", "display_value")
    @classmethod
    def _required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("ranked item text must not be empty")
        return cleaned

    @field_validator("percentage", "metric_value")
    @classmethod
    def _finite_number(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("ranked item numeric values must be finite")
        return value

    @field_validator("metric_unit")
    @classmethod
    def _metric_unit(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("attributes")
    @classmethod
    def _copy_attributes(cls, value: dict[str, Any]) -> dict[str, Any]:
        return freeze_mapping(value)
