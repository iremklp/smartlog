"""Deterministic, evidence-backed analysis insight model."""

from __future__ import annotations

import json
import math
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .immutable import FrozenDict, freeze_mapping

InsightLevel = Literal["info", "warning", "critical"]


class AnalysisInsight(BaseModel):
    """A cautious deterministic observation; it is not an AI or RCA claim."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    level: InsightLevel
    title: str
    message: str
    metric: str | None = None
    current_value: int | float | None = None
    reference_value: int | float | None = None
    unit: str | None = None
    evidence: dict[str, Any] = Field(default_factory=FrozenDict)
    recommendations: tuple[str, ...] = ()

    @field_validator("code")
    @classmethod
    def _code(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{1,63}", cleaned):
            raise ValueError("insight code must be a safe uppercase identifier")
        return cleaned

    @field_validator("title", "message")
    @classmethod
    def _required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("insight text must not be empty")
        return cleaned

    @field_validator("metric", "unit")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("current_value", "reference_value")
    @classmethod
    def _finite_values(cls, value: int | float | None) -> int | float | None:
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("insight numeric values must be finite")
        return value

    @field_validator("evidence")
    @classmethod
    def _safe_evidence(cls, value: dict[str, Any]) -> dict[str, Any]:
        try:
            encoded = json.dumps(
                value,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("insight evidence must be JSON-safe") from exc
        if len(encoded.encode("utf-8")) > 32_768:
            raise ValueError("insight evidence is too large")
        copied = json.loads(encoded)
        if not isinstance(copied, dict):  # pragma: no cover - input is a dict
            raise ValueError("insight evidence must be an object")
        return freeze_mapping(copied)

    @field_validator("recommendations")
    @classmethod
    def _recommendations(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        result = tuple(
            dict.fromkeys(item.strip() for item in value if item.strip())
        )
        if len(result) > 20:
            raise ValueError("too many insight recommendations")
        if any(len(item) > 500 for item in result):
            raise ValueError("insight recommendation is too long")
        return result
