from __future__ import annotations

import threading
from datetime import datetime
from typing import TypedDict

from pydantic import BaseModel, ConfigDict, Field

from log_parser_engine.models import EventStoreStatistics


class ApplicationRuntimeStatistics(BaseModel):
    """Runtime snapshot for the application service."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    created_at: datetime
    observed_at: datetime
    uptime_ms: float
    parser_count: int
    enabled_parser_count: int
    store_statistics: EventStoreStatistics
    startup_warnings: tuple[str, ...] = Field(default_factory=tuple)
    analysis_operations_total: int = 0
    analysis_operations_failed: int = 0
    comparison_operations_total: int = 0
    comparison_operations_failed: int = 0
    analyzed_events_total: int = 0
    average_analysis_duration_ms: float = 0.0
    maximum_analysis_duration_ms: float = 0.0


class AnalysisRuntimeMetricsSnapshot(TypedDict):
    analysis_operations_total: int
    analysis_operations_failed: int
    comparison_operations_total: int
    comparison_operations_failed: int
    analyzed_events_total: int
    average_analysis_duration_ms: float
    maximum_analysis_duration_ms: float


class AnalysisRuntimeMetrics:
    """Thread-safe, bounded-cardinality counters for analysis operations."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._analysis_operations_total = 0
        self._analysis_operations_failed = 0
        self._comparison_operations_total = 0
        self._comparison_operations_failed = 0
        self._analyzed_events_total = 0
        self._analysis_duration_total_ms = 0.0
        self._maximum_analysis_duration_ms = 0.0

    def record_analysis(
        self,
        *,
        event_count: int,
        duration_ms: float,
        failed: bool = False,
    ) -> None:
        self._record(
            comparison=False,
            event_count=event_count,
            duration_ms=duration_ms,
            failed=failed,
        )

    def record_comparison(
        self,
        *,
        event_count: int,
        duration_ms: float,
        failed: bool = False,
    ) -> None:
        self._record(
            comparison=True,
            event_count=event_count,
            duration_ms=duration_ms,
            failed=failed,
        )

    def snapshot(self) -> AnalysisRuntimeMetricsSnapshot:
        with self._lock:
            completed = self._analysis_operations_total
            average = (
                self._analysis_duration_total_ms / completed
                if completed
                else 0.0
            )
            return {
                "analysis_operations_total": self._analysis_operations_total,
                "analysis_operations_failed": self._analysis_operations_failed,
                "comparison_operations_total": self._comparison_operations_total,
                "comparison_operations_failed": self._comparison_operations_failed,
                "analyzed_events_total": self._analyzed_events_total,
                "average_analysis_duration_ms": average,
                "maximum_analysis_duration_ms": self._maximum_analysis_duration_ms,
            }

    def _record(
        self,
        *,
        comparison: bool,
        event_count: int,
        duration_ms: float,
        failed: bool,
    ) -> None:
        safe_events = max(0, event_count)
        safe_duration = max(0.0, duration_ms)
        with self._lock:
            if comparison:
                self._comparison_operations_total += 1
                if failed:
                    self._comparison_operations_failed += 1
            else:
                self._analysis_operations_total += 1
                if failed:
                    self._analysis_operations_failed += 1
                self._analysis_duration_total_ms += safe_duration
                self._maximum_analysis_duration_ms = max(
                    self._maximum_analysis_duration_ms,
                    safe_duration,
                )
            self._analyzed_events_total += safe_events
