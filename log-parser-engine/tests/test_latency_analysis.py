from __future__ import annotations

import statistics
from datetime import datetime, timedelta, timezone

import pytest

from log_parser_engine.analysis.latency import analyze_latency
from log_parser_engine.analysis.options import AnalysisOptions
from log_parser_engine.models.analysis_request import AnalysisRequest
from log_parser_engine.models.enums import LogSeverity, LogSourceType
from log_parser_engine.models.log_event import LogEvent
from log_parser_engine.models.stored_event import StoredEvent

BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def make_event(index: int, **updates: object) -> StoredEvent:
    values: dict[str, object] = {
        "timestamp": BASE + timedelta(seconds=index),
        "source_type": LogSourceType.HTTP,
        "severity": LogSeverity.INFO,
        "message": f"message {index}",
        "raw_message": f"raw {index}",
        "service": "api",
        "event_type": "request",
        "http_path": f"/items/{index}",
    }
    values.update(updates)
    return StoredEvent(
        id=f"evt-{index}",
        event=LogEvent(**values),
        inserted_at=BASE,
        sequence=index + 1,
        content_hash=f"{index + 1:064x}",
        estimated_size_bytes=100,
    )


def test_latency_coverage_units_percentiles_and_buckets() -> None:
    events = (
        make_event(0, duration_ms=5),
        make_event(1, attributes={"request_time": 0.1}),
        make_event(2, attributes={"duration_us": 250_000}),
        make_event(3),
        make_event(4, attributes={"latency_ms": "bad"}),
    )
    result = analyze_latency(events, AnalysisRequest(top_n=3))
    assert result.total_events == 5
    assert result.sample_count == 3
    assert result.missing_count == 1
    assert result.invalid_count == 1
    assert result.minimum_ms == 5
    assert result.maximum_ms == 250
    assert result.percentiles.percentile_values[50.0] == 100
    assert sum(bucket.count for bucket in result.latency_buckets) == 3
    assert result.detected_field == "duration_ms"


def test_numeric_string_is_supported_only_in_non_strict_mode() -> None:
    event = make_event(0, attributes={"latency_ms": "12.5"})
    strict = analyze_latency((event,), AnalysisRequest())
    relaxed = analyze_latency(
        (event,),
        AnalysisRequest(),
        options=AnalysisOptions(strict_numeric_values=False),
    )
    assert strict.invalid_count == 1
    assert relaxed.mean_ms == 12.5


def test_extreme_finite_duration_is_rejected_without_overflow() -> None:
    events = (
        make_event(0, duration_ms=1e308),
        make_event(1, duration_ms=0.0),
    )

    result = analyze_latency(events, AnalysisRequest())

    assert result.sample_count == 1
    assert result.invalid_count == 1
    assert result.mean_ms == 0.0
    assert result.standard_deviation_ms == 0.0


def test_slowest_events_and_group_rankings_are_deterministic() -> None:
    events = (
        make_event(
            0,
            duration_ms=50,
            service="beta",
            event_type="read",
            http_path="/b?x=1",
        ),
        make_event(
            1,
            duration_ms=50,
            service="alpha",
            event_type="read",
            http_path="/a/",
        ),
        make_event(
            2,
            duration_ms=10,
            service="alpha",
            event_type="write",
            http_path="/a",
        ),
    )
    result = analyze_latency(events, AnalysisRequest(top_n=2))
    assert [item.event_id for item in result.slowest_events] == ["evt-0", "evt-1"]
    assert [item.key for item in result.per_service] == ["alpha", "beta"]
    assert result.per_endpoint[0].key == "/a"
    assert result.per_endpoint[0].sample_count == 2
    assert result.slowest_events[0].message_preview == "message 0"


def test_empty_latency_result_is_consistent() -> None:
    result = analyze_latency((), AnalysisRequest())
    assert result.sample_count == 0
    assert result.mean_ms is None
    assert result.percentiles.sample_count == 0
    assert result.slowest_events == ()


def test_sampled_order_statistics_preserve_exact_streaming_descriptives() -> None:
    values = list(range(100))
    events = tuple(
        make_event(index, duration_ms=value)
        for index, value in enumerate(values)
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
    assert result.minimum_ms == 0
    assert result.maximum_ms == 99
    assert result.mean_ms == 49.5
    assert result.median_ms == result.percentiles.median
    assert 0 <= result.median_ms <= 99
    assert result.standard_deviation_ms == pytest.approx(
        statistics.pstdev(values)
    )
    assert result.percentiles.sample_count == result.sample_count
    assert result.percentiles.percentile_sample_count == 10
    assert result.percentiles.percentiles_approximated is True
    assert result.warnings == ("PERCENTILE_SAMPLED",)
