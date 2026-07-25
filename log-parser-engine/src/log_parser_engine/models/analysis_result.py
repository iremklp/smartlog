"""Top-level statistical analysis result models."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .analysis_insight import AnalysisInsight
from .analysis_request import AnalysisRequest
from .analysis_summary import AnalysisSummary
from .distribution import DistributionResult
from .enums import LogSeverity, LogSourceType
from .http_analysis import HTTPAnalysis
from .immutable import FrozenDict, freeze_mapping
from .latency_analysis import LatencyAnalysis
from .timeline import TimelineResult


class AnalysisEventSample(BaseModel):
    """Bounded UI sample that deliberately excludes raw log content."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str
    timestamp: datetime
    severity: LogSeverity
    source_type: LogSourceType
    message_preview: str = Field(max_length=1_000)
    event_type: str | None = None
    service: str | None = None
    host: str | None = None
    parser_name: str | None = None

    @field_validator("event_id", "message_preview")
    @classmethod
    def _required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("analysis sample text must not be empty")
        return cleaned

    @field_validator("timestamp")
    @classmethod
    def _aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("analysis sample timestamp must be timezone-aware")
        return value

    @field_validator("event_type", "service", "host", "parser_name")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class AnalysisResult(BaseModel):
    """Complete immutable output from a statistical analysis execution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    analysis_id: UUID = Field(default_factory=uuid4)
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    request: AnalysisRequest
    input_event_count: int = Field(ge=0)
    matched_event_count: int = Field(ge=0)
    analysis_duration_ms: float = Field(ge=0)
    summary: AnalysisSummary | None = None
    timeline: TimelineResult | None = None
    distributions: tuple[DistributionResult, ...] = ()
    latency: LatencyAnalysis | None = None
    http: HTTPAnalysis | None = None
    insights: tuple[AnalysisInsight, ...] = ()
    samples: tuple[AnalysisEventSample, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=FrozenDict)

    @field_validator("generated_at")
    @classmethod
    def _generated_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("generated_at must be timezone-aware")
        return value.astimezone(timezone.utc)

    @field_validator("analysis_duration_ms")
    @classmethod
    def _finite_duration(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("analysis_duration_ms must be finite")
        return value

    @field_validator("warnings")
    @classmethod
    def _warnings(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(item.strip() for item in value if item.strip())
        )

    @field_validator("metadata")
    @classmethod
    def _metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        try:
            encoded = json.dumps(value, allow_nan=False, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("analysis metadata must be JSON-safe") from exc
        copied = json.loads(encoded)
        if not isinstance(copied, dict):  # pragma: no cover - input is a dict
            raise ValueError("analysis metadata must be an object")
        return freeze_mapping(copied)

    @model_validator(mode="after")
    def _result_consistency(self) -> "AnalysisResult":
        if self.matched_event_count > self.input_event_count:
            raise ValueError("matched_event_count cannot exceed input_event_count")
        if self.summary is not None and (
            self.summary.input_event_count != self.input_event_count
            or self.summary.matched_event_count != self.matched_event_count
        ):
            raise ValueError("analysis summary counts must match result counts")
        if not self.request.include_samples and self.samples:
            raise ValueError("samples require include_samples=True")
        if len(self.samples) > self.request.sample_size:
            raise ValueError("sample count exceeds the requested sample_size")
        return self
