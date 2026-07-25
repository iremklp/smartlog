"""Statistical comparison result models."""

from __future__ import annotations

import json
import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .analysis_insight import AnalysisInsight
from .analysis_summary import AnalysisSummary
from .immutable import FrozenDict, freeze_mapping

ChangeDirection = Literal[
    "increase",
    "decrease",
    "unchanged",
    "new",
    "removed",
    "undefined",
]
MetricInterpretation = Literal["improved", "degraded", "neutral", "unknown"]


def _optional_finite(value: float | None) -> float | None:
    if value is not None and not math.isfinite(value):
        raise ValueError("comparison numeric values must be finite")
    return value


def _normalized_notes(value: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item.strip() for item in value if item.strip()))


class MetricComparison(BaseModel):
    """Change in one well-defined metric between two analysis periods."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    metric: str
    unit: str | None = None
    baseline_value: float | None = None
    comparison_value: float | None = None
    absolute_change: float | None = None
    percent_change: float | None = None
    direction: ChangeDirection
    significant: bool
    interpretation: MetricInterpretation
    notes: tuple[str, ...] = ()

    @field_validator("metric")
    @classmethod
    def _metric(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("comparison metric must not be empty")
        return cleaned

    @field_validator("unit")
    @classmethod
    def _unit(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator(
        "baseline_value",
        "comparison_value",
        "absolute_change",
        "percent_change",
    )
    @classmethod
    def _finite_numbers(cls, value: float | None) -> float | None:
        return _optional_finite(value)

    @field_validator("notes")
    @classmethod
    def _notes(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _normalized_notes(value)

    @model_validator(mode="after")
    def _direction_consistency(self) -> "MetricComparison":
        if self.direction == "undefined" and (
            self.baseline_value is not None and self.comparison_value is not None
        ):
            raise ValueError("undefined comparisons must have a missing value")
        if self.direction == "new" and self.comparison_value is None:
            raise ValueError("new comparisons require a comparison value")
        if self.direction == "removed" and self.baseline_value is None:
            raise ValueError("removed comparisons require a baseline value")
        return self


class GroupComparison(BaseModel):
    """Change in the prevalence and metrics of one categorical group."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    group_field: str
    key: str
    baseline_count: int = Field(ge=0)
    comparison_count: int = Field(ge=0)
    absolute_change: int
    percent_change: float | None = None
    baseline_percentage: float = Field(ge=0, le=100)
    comparison_percentage: float = Field(ge=0, le=100)
    percentage_point_change: float
    new_group: bool = False
    disappeared_group: bool = False
    significant: bool = False
    metric_comparisons: tuple[MetricComparison, ...] = ()
    attributes: dict[str, Any] = Field(default_factory=FrozenDict)

    @field_validator("group_field", "key")
    @classmethod
    def _required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("group comparison text must not be empty")
        return cleaned

    @field_validator(
        "percent_change",
        "baseline_percentage",
        "comparison_percentage",
        "percentage_point_change",
    )
    @classmethod
    def _finite_numbers(cls, value: float | None) -> float | None:
        return _optional_finite(value)

    @field_validator("attributes")
    @classmethod
    def _attributes(cls, value: dict[str, Any]) -> dict[str, Any]:
        return freeze_mapping(value)

    @model_validator(mode="after")
    def _group_consistency(self) -> "GroupComparison":
        if self.absolute_change != self.comparison_count - self.baseline_count:
            raise ValueError("absolute_change does not match group counts")
        if self.new_group and self.disappeared_group:
            raise ValueError("a group cannot be both new and disappeared")
        if self.new_group and self.baseline_count != 0:
            raise ValueError("new groups must have a zero baseline count")
        if self.disappeared_group and self.comparison_count != 0:
            raise ValueError("disappeared groups must have a zero comparison count")
        return self


class ComparisonResult(BaseModel):
    """Complete deterministic comparison of baseline and comparison snapshots."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    baseline_label: str
    comparison_label: str
    baseline_summary: AnalysisSummary
    comparison_summary: AnalysisSummary
    baseline_event_count: int = Field(ge=0)
    comparison_event_count: int = Field(ge=0)
    duration_ms: float = Field(ge=0)
    metric_comparisons: tuple[MetricComparison, ...] = ()
    group_comparisons: tuple[GroupComparison, ...] = ()
    insights: tuple[AnalysisInsight, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=FrozenDict)

    @field_validator("baseline_label", "comparison_label")
    @classmethod
    def _labels(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned or len(cleaned) > 100:
            raise ValueError("comparison labels must be 1-100 characters")
        return cleaned

    @field_validator("duration_ms")
    @classmethod
    def _finite_duration(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("comparison duration must be finite")
        return value

    @field_validator("warnings")
    @classmethod
    def _warnings(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _normalized_notes(value)

    @field_validator("metadata")
    @classmethod
    def _metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        try:
            encoded = json.dumps(value, allow_nan=False, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("comparison metadata must be JSON-safe") from exc
        copied = json.loads(encoded)
        if not isinstance(copied, dict):  # pragma: no cover - input is a dict
            raise ValueError("comparison metadata must be an object")
        return freeze_mapping(copied)

    @model_validator(mode="after")
    def _event_count_consistency(self) -> "ComparisonResult":
        if self.baseline_event_count != self.baseline_summary.matched_event_count:
            raise ValueError("baseline event count must match baseline summary")
        if self.comparison_event_count != self.comparison_summary.matched_event_count:
            raise ValueError("comparison event count must match comparison summary")
        return self
