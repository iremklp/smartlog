from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from log_parser_engine.analysis.options import AnalysisOptions
from log_parser_engine.analysis.timelines import build_timeline
from log_parser_engine.exceptions.analysis import AnalysisTimelineLimitError
from log_parser_engine.models.analysis_request import AnalysisRequest
from log_parser_engine.models.enums import LogSeverity, LogSourceType
from log_parser_engine.models.log_event import LogEvent
from log_parser_engine.models.stored_event import StoredEvent

UTC = timezone.utc
BASE = datetime(2026, 1, 1, tzinfo=UTC)


def make_event(
    index: int,
    seconds: int,
    *,
    severity: LogSeverity = LogSeverity.INFO,
    duration: float | None = None,
    status: int | None = None,
) -> StoredEvent:
    event = LogEvent(
        timestamp=BASE + timedelta(seconds=seconds),
        source_type=LogSourceType.HTTP,
        severity=severity,
        message=f"event {index}",
        raw_message=f"event {index}",
        duration_ms=duration,
        http_status=status,
    )
    return StoredEvent(
        id=f"evt-{index}",
        event=event,
        inserted_at=BASE,
        sequence=index + 1,
        content_hash=f"{index + 1:064x}",
        estimated_size_bytes=100,
    )


def test_epoch_aligned_timeline_includes_empty_buckets_and_metrics() -> None:
    events = (
        make_event(0, 10, duration=10, status=200),
        make_event(1, 100, severity=LogSeverity.ERROR, duration=30, status=503),
        make_event(2, 600, severity=LogSeverity.CRITICAL, duration=50, status=500),
    )
    result = build_timeline(
        events,
        AnalysisRequest(
            time_bucket_seconds=300,
            start_time=BASE,
            end_time=BASE + timedelta(minutes=15),
        ),
    )
    assert result.start == BASE
    assert result.end == BASE + timedelta(minutes=15)
    assert len(result.buckets) == 3
    assert [bucket.event_count for bucket in result.buckets] == [2, 0, 1]
    assert result.empty_bucket_count == 1
    assert result.buckets[0].error_rate == 0.5
    assert result.buckets[0].average_duration_ms == 20
    assert result.buckets[0].p95_duration_ms == 30
    assert result.buckets[0].status_5xx_count == 1
    assert result.peak_bucket_start == BASE


def test_boundary_is_start_inclusive_and_end_exclusive() -> None:
    events = (
        make_event(0, 0),
        make_event(1, 300),
        make_event(2, 600),
    )
    result = build_timeline(
        events,
        AnalysisRequest(
            time_bucket_seconds=300,
            start_time=BASE,
            end_time=BASE + timedelta(seconds=600),
        ),
    )
    assert [bucket.event_count for bucket in result.buckets] == [1, 1]


def test_explicit_bucket_limit_errors_but_default_bucket_adjusts() -> None:
    events = (make_event(0, 0), make_event(1, 600))
    with pytest.raises(AnalysisTimelineLimitError):
        build_timeline(
            events,
            AnalysisRequest(
                time_bucket_seconds=60,
                start_time=BASE,
                end_time=BASE + timedelta(minutes=10),
            ),
            options=AnalysisOptions(max_timeline_buckets=2),
        )

    adjusted = build_timeline(
        events,
        AnalysisRequest(
            start_time=BASE,
            end_time=BASE + timedelta(minutes=10),
        ),
        options=AnalysisOptions(
            default_time_bucket_seconds=60,
            max_timeline_buckets=2,
        ),
    )
    assert adjusted.bucket_seconds == 300
    assert adjusted.warnings == ("TIME_BUCKET_ADJUSTED",)


def test_out_of_order_input_still_returns_ordered_buckets() -> None:
    result = build_timeline(
        (make_event(0, 600), make_event(1, 0), make_event(2, 300)),
        AnalysisRequest(time_bucket_seconds=300),
    )
    assert [bucket.start for bucket in result.buckets] == sorted(
        bucket.start for bucket in result.buckets
    )


def test_empty_snapshot_without_range_is_empty() -> None:
    result = build_timeline((), AnalysisRequest())
    assert result.buckets == ()
    assert result.start is None
    assert result.end is None


def test_timeline_rejects_datetime_upper_bound_without_overflow() -> None:
    timestamp = datetime(9999, 12, 31, 23, 59, tzinfo=UTC)
    event = StoredEvent(
        id="evt-upper-bound",
        event=LogEvent(
            timestamp=timestamp,
            source_type=LogSourceType.HTTP,
            severity=LogSeverity.INFO,
            message="upper-bound event",
            raw_message="upper-bound event",
        ),
        inserted_at=timestamp,
        sequence=1,
        content_hash="f" * 64,
        estimated_size_bytes=100,
    )

    with pytest.raises(
        AnalysisTimelineLimitError,
        match="supported datetime bounds",
    ):
        build_timeline((event,), AnalysisRequest())
