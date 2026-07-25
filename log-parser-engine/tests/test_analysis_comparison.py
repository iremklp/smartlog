from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from log_parser_engine.analysis import StatisticalAnalysisEngine
from log_parser_engine.analysis.options import AnalysisOptions
from log_parser_engine.models import (
    ComparisonRequest,
    LogEvent,
    LogSeverity,
    LogSourceType,
    StoredEvent,
)


def _event(
    index: int,
    *,
    severity: LogSeverity,
    service: str,
    status: int,
    duration: float,
) -> StoredEvent:
    timestamp = datetime(2026, 7, 25, 8, tzinfo=timezone.utc) + timedelta(
        minutes=index
    )
    return StoredEvent(
        id=f"comparison-{index}-{severity.value}",
        event=LogEvent(
            timestamp=timestamp,
            source_type=LogSourceType.HTTP,
            severity=severity,
            message="synthetic comparison event",
            raw_message="secret raw comparison event",
            service=service,
            http_method="GET",
            http_path="/api/health",
            http_status=status,
            duration_ms=duration,
        ),
        inserted_at=timestamp,
        sequence=index + 1,
        content_hash=f"{index + status:064x}",
        estimated_size_bytes=512,
    )


def test_comparison_marks_error_and_latency_increases_as_degraded() -> None:
    baseline = (
        _event(
            0,
            severity=LogSeverity.INFO,
            service="gateway",
            status=200,
            duration=20,
        ),
        _event(
            1,
            severity=LogSeverity.INFO,
            service="gateway",
            status=200,
            duration=25,
        ),
    )
    comparison = (
        _event(
            10,
            severity=LogSeverity.ERROR,
            service="gateway",
            status=500,
            duration=200,
        ),
        _event(
            11,
            severity=LogSeverity.ERROR,
            service="gateway",
            status=500,
            duration=250,
        ),
    )

    result = StatisticalAnalysisEngine(
        AnalysisOptions(minimum_comparison_count=2)
    ).compare(
        baseline,
        comparison,
        ComparisonRequest(
            metrics=("error_rate", "p95_duration_ms", "server_error_rate"),
            group_by=("service",),
            significant_change_percent=20,
        ),
    )

    metrics = {metric.metric: metric for metric in result.metric_comparisons}
    assert metrics["error_rate"].direction == "new"
    assert metrics["error_rate"].interpretation == "unknown"
    assert metrics["p95_duration_ms"].direction == "increase"
    assert metrics["p95_duration_ms"].interpretation == "degraded"
    assert any(insight.code == "ERROR_SPIKE" for insight in result.insights)


def test_comparison_handles_zero_baseline_without_fake_percentage() -> None:
    comparison = (
        _event(
            1,
            severity=LogSeverity.ERROR,
            service="new-service",
            status=500,
            duration=100,
        ),
    )
    result = StatisticalAnalysisEngine().compare(
        (),
        comparison,
        ComparisonRequest(
            metrics=("event_count",),
            group_by=("service",),
            minimum_group_count=1,
        ),
    )

    metric = result.metric_comparisons[0]
    assert metric.direction == "new"
    assert metric.percent_change is None
    assert result.group_comparisons[0].new_group is True
    assert result.group_comparisons[0].percent_change is None
    assert "baseline dataset contains no matching events" in result.warnings


def test_comparison_handles_percent_change_numeric_overflow() -> None:
    baseline = (
        _event(
            0,
            severity=LogSeverity.INFO,
            service="gateway",
            status=200,
            duration=5e-324,
        ),
    )
    comparison = (
        _event(
            1,
            severity=LogSeverity.INFO,
            service="gateway",
            status=200,
            duration=1e100,
        ),
    )

    result = StatisticalAnalysisEngine(
        AnalysisOptions(minimum_comparison_count=1)
    ).compare(
        baseline,
        comparison,
        ComparisonRequest(
            metrics=("average_duration_ms",),
            group_by=(),
        ),
    )

    metric = result.metric_comparisons[0]
    assert metric.direction == "increase"
    assert metric.percent_change is None
    assert metric.significant
    assert "percent change exceeds finite numeric range" in metric.notes


def test_throughput_normalization_is_explicit_and_preserves_raw_counts() -> None:
    baseline = (
        _event(
            0,
            severity=LogSeverity.INFO,
            service="gateway",
            status=200,
            duration=20,
        ),
        _event(
            60,
            severity=LogSeverity.INFO,
            service="gateway",
            status=200,
            duration=20,
        ),
    )
    comparison = tuple(
        _event(
            index,
            severity=LogSeverity.INFO,
            service="gateway",
            status=200,
            duration=20,
        )
        for index in (1_000, 1_040, 1_080, 1_120)
    )
    engine = StatisticalAnalysisEngine()

    normalized = engine.compare(
        baseline,
        comparison,
        ComparisonRequest(
            metrics=("event_count", "throughput"),
            group_by=(),
            normalize_by_time_span=True,
        ),
    )
    raw = engine.compare(
        baseline,
        comparison,
        ComparisonRequest(
            metrics=("event_count", "throughput"),
            group_by=(),
            normalize_by_time_span=False,
        ),
    )

    normalized_metrics = {
        metric.metric: metric for metric in normalized.metric_comparisons
    }
    raw_metrics = {metric.metric: metric for metric in raw.metric_comparisons}
    assert normalized_metrics["event_count"].baseline_value == 2
    assert normalized_metrics["event_count"].comparison_value == 4
    assert raw_metrics["event_count"].baseline_value == 2
    assert raw_metrics["event_count"].comparison_value == 4

    normalized_throughput = normalized_metrics["throughput"]
    assert normalized_throughput.unit == "events_per_minute"
    assert normalized_throughput.direction == "unchanged"
    assert normalized_throughput.baseline_value == pytest.approx(
        normalized_throughput.comparison_value
    )
    assert "normalized by observed time span" in normalized_throughput.notes

    raw_throughput = raw_metrics["throughput"]
    assert raw_throughput.unit == "count"
    assert raw_throughput.baseline_value == 2
    assert raw_throughput.comparison_value == 4
    assert raw_throughput.direction == "increase"
    assert (
        "time-span normalization disabled; raw event counts compared"
        in raw_throughput.notes
    )


def test_event_count_comparison_skips_latency_and_http_analysis() -> None:
    events = (
        _event(
            0,
            severity=LogSeverity.INFO,
            service="gateway",
            status=200,
            duration=20,
        ),
    )

    with (
        patch(
            "log_parser_engine.analysis.comparison.analyze_latency",
            side_effect=AssertionError("latency analysis must not run"),
        ),
        patch(
            "log_parser_engine.analysis.comparison.analyze_http",
            side_effect=AssertionError("HTTP analysis must not run"),
        ),
    ):
        result = StatisticalAnalysisEngine().compare(
            events,
            events,
            ComparisonRequest(metrics=("event_count",), group_by=()),
        )

    assert result.metric_comparisons[0].metric == "event_count"


def test_latency_metrics_do_not_trigger_http_analysis() -> None:
    events = (
        _event(
            0,
            severity=LogSeverity.INFO,
            service="gateway",
            status=200,
            duration=20,
        ),
        _event(
            1,
            severity=LogSeverity.INFO,
            service="gateway",
            status=200,
            duration=30,
        ),
    )

    with patch(
        "log_parser_engine.analysis.comparison.analyze_http",
        side_effect=AssertionError("HTTP analysis must not run"),
    ):
        result = StatisticalAnalysisEngine().compare(
            events,
            events,
            ComparisonRequest(
                metrics=("average_duration_ms", "p95_duration_ms"),
                group_by=(),
            ),
        )

    assert tuple(
        metric.metric for metric in result.metric_comparisons
    ) == ("average_duration_ms", "p95_duration_ms")


def test_http_metrics_do_not_trigger_latency_analysis() -> None:
    events = (
        _event(
            0,
            severity=LogSeverity.INFO,
            service="gateway",
            status=200,
            duration=20,
        ),
        _event(
            1,
            severity=LogSeverity.ERROR,
            service="gateway",
            status=500,
            duration=30,
        ),
    )

    with patch(
        "log_parser_engine.analysis.comparison.analyze_latency",
        side_effect=AssertionError("latency analysis must not run"),
    ):
        result = StatisticalAnalysisEngine().compare(
            events,
            events,
            ComparisonRequest(
                metrics=("server_error_rate", "client_error_rate"),
                group_by=(),
            ),
        )

    assert tuple(
        metric.metric for metric in result.metric_comparisons
    ) == ("server_error_rate", "client_error_rate")
