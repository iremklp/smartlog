from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from log_parser_engine.analysis import AnalysisOptions, StatisticalAnalysisEngine
from log_parser_engine.exceptions import AnalysisEventLimitError
from log_parser_engine.models import (
    AnalysisRequest,
    EventFilter,
    LogEvent,
    LogSeverity,
    LogSourceType,
    StoredEvent,
)


def _stored(
    index: int,
    *,
    severity: LogSeverity = LogSeverity.INFO,
    service: str = "catalog",
    status: int | None = None,
    duration: float | None = None,
) -> StoredEvent:
    timestamp = datetime(2026, 7, 25, 10, tzinfo=timezone.utc) + timedelta(
        minutes=index
    )
    event = LogEvent(
        timestamp=timestamp,
        source_type=LogSourceType.HTTP if status else LogSourceType.APPLICATION,
        severity=severity,
        event_type="request",
        message=f"event {index}",
        raw_message=f"raw secret {index}",
        service=service,
        host=f"node-{index % 2}",
        http_method="GET" if status else None,
        http_path="/api/items" if status else None,
        http_status=status,
        duration_ms=duration,
        attributes={"parser_name": "json_log"},
    )
    return StoredEvent(
        id=f"event-{index}",
        event=event,
        inserted_at=timestamp,
        sequence=index + 1,
        content_hash=f"{index + 1:064x}",
        estimated_size_bytes=512,
    )


def test_engine_builds_requested_modules_without_mutating_events() -> None:
    events = (
        _stored(0, duration=10),
        _stored(
            1,
            severity=LogSeverity.ERROR,
            service="checkout",
            status=500,
            duration=250,
        ),
    )
    before = tuple(event.model_dump() for event in events)

    result = StatisticalAnalysisEngine().analyze(
        events,
        AnalysisRequest(
            time_bucket_seconds=60,
            include_samples=True,
            sample_size=2,
        ),
    )

    assert result.input_event_count == 2
    assert result.matched_event_count == 2
    assert result.summary is not None
    assert result.summary.error_count == 1
    assert result.timeline is not None
    assert result.latency is not None
    assert result.http is not None
    assert len(result.distributions) > 0
    assert len(result.samples) == 2
    assert all("raw secret" not in item.message_preview for item in result.samples)
    assert tuple(event.model_dump() for event in events) == before


def test_engine_uses_safe_placeholder_for_control_only_sample_message() -> None:
    event = _stored(0).model_copy(
        update={
            "event": _stored(0).event.model_copy(
                update={"message": "\x01"},
            )
        }
    )

    result = StatisticalAnalysisEngine().analyze(
        (event,),
        AnalysisRequest(include_samples=True, sample_size=1),
    )

    assert result.samples[0].message_preview == "[empty after sanitization]"


def test_engine_filter_semantics_and_selective_modules() -> None:
    events = (
        _stored(0, service="catalog"),
        _stored(1, severity=LogSeverity.ERROR, service="checkout"),
    )
    result = StatisticalAnalysisEngine().analyze(
        events,
        AnalysisRequest(
            filter=EventFilter(services=("checkout",)),
            include_timeline=False,
            include_distributions=False,
            include_latency=False,
            include_http=False,
            include_insights=False,
        ),
    )

    assert result.matched_event_count == 1
    assert result.summary is not None
    assert result.summary.error_count == 1
    assert result.timeline is None
    assert result.distributions == ()
    assert result.latency is None
    assert result.http is None


def test_engine_rejects_snapshots_over_the_configured_limit() -> None:
    engine = StatisticalAnalysisEngine(AnalysisOptions(max_events=1))

    with pytest.raises(AnalysisEventLimitError) as exc_info:
        engine.analyze((_stored(0), _stored(1)), AnalysisRequest())

    assert exc_info.value.count == 2
    assert exc_info.value.limit == 1


def test_engine_is_stateless_across_calls() -> None:
    engine = StatisticalAnalysisEngine()
    events = (_stored(0),)

    first = engine.analyze(events, AnalysisRequest())
    second = engine.analyze(events, AnalysisRequest())

    assert first.analysis_id != second.analysis_id
    assert first.summary == second.summary
    assert first.distributions == second.distributions
