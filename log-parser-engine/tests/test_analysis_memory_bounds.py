from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

import pytest

from log_parser_engine.analysis import StatisticalAnalysisEngine
from log_parser_engine.analysis.comparison import compare_event_snapshots
from log_parser_engine.analysis.http_analysis import analyze_http
from log_parser_engine.analysis.latency import analyze_latency
from log_parser_engine.analysis.options import AnalysisOptions
from log_parser_engine.analysis.sampling import BoundedDeterministicSample
from log_parser_engine.analysis.summary import summarize_events
from log_parser_engine.analysis.timelines import build_timeline
from log_parser_engine.exceptions.analysis import (
    AnalysisGroupLimitError,
    AnalysisNumericValueError,
    AnalysisSampleLimitError,
)
from log_parser_engine.models.analysis_request import AnalysisRequest, ComparisonRequest
from log_parser_engine.models.enums import LogSeverity, LogSourceType
from log_parser_engine.models.log_event import LogEvent
from log_parser_engine.models.stored_event import StoredEvent

BASE = datetime(2026, 7, 25, tzinfo=timezone.utc)


def make_event(
    index: int,
    *,
    service: str = "api",
    endpoint: str = "/items",
    duration: float | None = None,
    severity: LogSeverity = LogSeverity.INFO,
    status: int | None = 200,
    attributes: dict[str, object] | None = None,
) -> StoredEvent:
    timestamp = BASE + timedelta(seconds=index)
    return StoredEvent(
        id=f"event-{index}",
        event=LogEvent(
            timestamp=timestamp,
            source_type=LogSourceType.HTTP,
            severity=severity,
            event_type="request",
            message=f"event {index}",
            raw_message=f"raw event {index}",
            service=service,
            http_method="GET",
            http_path=endpoint,
            http_status=status,
            duration_ms=duration,
            attributes=attributes or {},
        ),
        inserted_at=timestamp,
        sequence=index + 1,
        content_hash=f"{index + 1:064x}",
        estimated_size_bytes=100,
    )


def test_bounded_sample_never_retains_more_than_configured_limit() -> None:
    sample = BoundedDeterministicSample[int](
        max_samples=7,
        allow_sampling=True,
    )
    for index in range(10_000):
        sample.add(index, key=f"event-{index}")

    assert sample.count == 10_000
    assert sample.retained_count == 7
    assert sample.sampled is True
    assert len(sample.values()) == 7


def test_exact_sample_limit_is_checked_before_append() -> None:
    sample = BoundedDeterministicSample[int](
        max_samples=2,
        allow_sampling=False,
    )
    sample.add(1, key="one")
    sample.add(2, key="two")

    with pytest.raises(AnalysisSampleLimitError):
        sample.add(3, key="three")

    assert sample.count == 2
    assert sample.values() == (1, 2)


def test_summary_bounds_response_dimensions_but_not_content_hashes() -> None:
    with pytest.raises(AnalysisGroupLimitError) as captured:
        summarize_events(
            tuple(
                make_event(index, service=f"service-{index}")
                for index in range(3)
            ),
            options=AnalysisOptions(max_groups=2),
        )
    assert captured.value.field == "service"

    result = summarize_events(
        tuple(make_event(index) for index in range(3)),
        options=AnalysisOptions(max_groups=2),
    )
    assert result.duplicate_content_count == 0


def test_timeline_rejects_exact_samples_before_unbounded_growth() -> None:
    events = tuple(make_event(index, duration=float(index)) for index in range(3))
    request = AnalysisRequest(time_bucket_seconds=60)

    with pytest.raises(AnalysisSampleLimitError):
        build_timeline(
            events,
            request,
            options=AnalysisOptions(
                max_percentile_samples=2,
                allow_percentile_sampling=False,
            ),
        )

    sampled = build_timeline(
        events,
        request,
        options=AnalysisOptions(
            max_percentile_samples=2,
            allow_percentile_sampling=True,
        ),
    )
    assert sampled.buckets[0].average_duration_ms == 1
    assert sampled.warnings == ("PERCENTILE_SAMPLED",)


def test_http_endpoint_samples_are_bounded_without_event_reference_lists() -> None:
    events = tuple(make_event(index, duration=float(index)) for index in range(3))
    request = AnalysisRequest(include_timeline=False)

    with pytest.raises(AnalysisSampleLimitError):
        analyze_http(
            events,
            request,
            options=AnalysisOptions(
                max_percentile_samples=2,
                allow_percentile_sampling=False,
            ),
        )

    sampled = analyze_http(
        events,
        request,
        options=AnalysisOptions(
            max_percentile_samples=2,
            allow_percentile_sampling=True,
            minimum_endpoint_latency_samples=1,
        ),
    )
    endpoint = sampled.slowest_endpoints[0]
    assert endpoint.request_count == 3
    assert endpoint.latency_sample_count == 3
    assert endpoint.average_duration_ms == 1
    assert sampled.timeline is None
    assert sampled.warnings == ("PERCENTILE_SAMPLED",)


def test_latency_order_statistics_sample_but_moments_cover_all_events() -> None:
    events = tuple(
        make_event(index, duration=float(index))
        for index in range(100)
    )
    result = analyze_latency(
        events,
        AnalysisRequest(),
        options=AnalysisOptions(
            max_percentile_samples=10,
            allow_percentile_sampling=True,
        ),
    )

    assert result.sample_count == 100
    assert result.mean_ms == 49.5
    assert result.minimum_ms == 0
    assert result.maximum_ms == 99
    assert result.median_ms == result.percentiles.median
    assert result.percentiles.percentile_sample_count == 10
    assert result.percentiles.percentiles_approximated is True


def test_comparison_group_limit_is_checked_before_counter_growth() -> None:
    events = tuple(
        make_event(index, endpoint=f"/endpoint-{index}")
        for index in range(3)
    )
    with pytest.raises(AnalysisGroupLimitError) as captured:
        compare_event_snapshots(
            events,
            events,
            ComparisonRequest(
                metrics=("event_count",),
                group_by=("endpoint",),
            ),
            options=AnalysisOptions(max_groups=2),
        )
    assert captured.value.field == "endpoint"
    assert captured.value.count == 3


def test_low_sample_comparisons_are_not_significant_or_insight_worthy() -> None:
    baseline = (make_event(0, severity=LogSeverity.INFO, status=200),)
    comparison = (make_event(1, severity=LogSeverity.ERROR, status=500),)
    result = StatisticalAnalysisEngine(
        AnalysisOptions(minimum_comparison_count=2)
    ).compare(
        baseline,
        comparison,
        ComparisonRequest(
            metrics=("error_rate", "server_error_rate"),
            group_by=(),
        ),
    )

    assert all(not metric.significant for metric in result.metric_comparisons)
    assert all(
        "LOW_SAMPLE_SIZE" in metric.notes
        for metric in result.metric_comparisons
    )
    assert result.insights == ()
    assert "LOW_SAMPLE_SIZE" in result.warnings


@pytest.mark.parametrize(
    "analyzer",
    [
        lambda events, request, options: summarize_events(
            events,
            options=options,
        ),
        build_timeline,
        analyze_latency,
        analyze_http,
    ],
)
def test_invalid_duration_policy_is_shared_across_analysis_modules(
    analyzer: Callable[..., object],
) -> None:
    events = (
        make_event(
            0,
            duration=None,
            attributes={"latency_ms": "not-a-number"},
        ),
    )
    with pytest.raises(AnalysisNumericValueError):
        analyzer(
            events,
            AnalysisRequest(include_timeline=False),
            options=AnalysisOptions(ignore_non_finite_values=False),
        )
