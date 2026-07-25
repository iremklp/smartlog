from __future__ import annotations

from datetime import datetime, timedelta, timezone

from log_parser_engine.analysis.distributions import build_distributions
from log_parser_engine.analysis.http_analysis import analyze_http
from log_parser_engine.analysis.insights import generate_insights
from log_parser_engine.analysis.latency import analyze_latency
from log_parser_engine.analysis.options import AnalysisOptions
from log_parser_engine.analysis.summary import summarize_events
from log_parser_engine.models.analysis_request import AnalysisRequest
from log_parser_engine.models.enums import LogSeverity, LogSourceType
from log_parser_engine.models.log_event import LogEvent
from log_parser_engine.models.stored_event import StoredEvent

BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def make_event(index: int, **updates: object) -> StoredEvent:
    values: dict[str, object] = {
        "timestamp": BASE + timedelta(seconds=index),
        "source_type": LogSourceType.APPLICATION,
        "severity": LogSeverity.INFO,
        "message": f"synthetic {index}",
        "raw_message": f"raw {index}",
        "service": "api",
        "host": "host-a",
        "event_type": "request",
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


def test_no_events_and_low_sample_insights() -> None:
    no_events = generate_insights(summary=summarize_events(()))
    assert [item.code for item in no_events] == ["NO_EVENTS"]

    low_sample = generate_insights(
        summary=summarize_events((make_event(0, duration_ms=1),))
    )
    assert "LOW_SAMPLE_SIZE" in {item.code for item in low_sample}


def test_error_and_critical_thresholds_have_deterministic_priority() -> None:
    events = tuple(
        make_event(
            index,
            severity=(
                LogSeverity.CRITICAL
                if index == 0
                else LogSeverity.ERROR
            ),
            duration_ms=1,
        )
        for index in range(10)
    )
    insights = generate_insights(
        summary=summarize_events(events),
        options=AnalysisOptions(
            error_rate_warning_threshold=0.1,
            error_rate_critical_threshold=0.5,
        ),
    )
    assert insights[0].level == "critical"
    assert [item.code for item in insights].count("HIGH_ERROR_RATE") == 1
    assert "HIGH_CRITICAL_RATE" in {item.code for item in insights}


def test_dominance_missing_duration_and_out_of_order() -> None:
    events = tuple(
        make_event(
            index,
            timestamp=BASE + timedelta(seconds=10 - index),
            duration_ms=(1 if index == 0 else None),
        )
        for index in range(10)
    )
    summary = summarize_events(events)
    distributions = build_distributions(
        events,
        fields=("service", "host", "event_type"),
        top_n=10,
    )
    insights = generate_insights(
        summary=summary,
        distributions=distributions,
    )
    codes = {item.code for item in insights}
    assert "SINGLE_SERVICE_CONCENTRATION" in codes
    assert "SINGLE_HOST_CONCENTRATION" in codes
    assert "DOMINANT_EVENT_TYPE" in codes
    assert "MISSING_DURATION_DATA" in codes
    assert "OUT_OF_ORDER_TIMESTAMPS" in codes


def test_latency_and_http_missing_status_insights() -> None:
    events = tuple(
        make_event(
            index,
            source_type=LogSourceType.HTTP,
            http_method="GET",
            http_path="/api",
            http_status=(503 if index == 0 else None),
            duration_ms=500,
        )
        for index in range(4)
    )
    request = AnalysisRequest()
    options = AnalysisOptions(
        latency_warning_percentile_ms=100,
        latency_critical_percentile_ms=1_000,
    )
    insights = generate_insights(
        summary=summarize_events(events),
        latency=analyze_latency(events, request, options=options),
        http=analyze_http(events, request, options=options),
        options=options,
    )
    codes = {item.code for item in insights}
    assert "LATENCY_P95_HIGH" in codes
    assert "MISSING_HTTP_STATUS_DATA" in codes


def test_no_false_positive_and_no_definitive_root_cause_language() -> None:
    events = tuple(
        make_event(index, duration_ms=10)
        for index in range(20)
    )
    insights = generate_insights(summary=summarize_events(events))
    assert "HIGH_ERROR_RATE" not in {item.code for item in insights}
    assert all("root cause" not in item.message.casefold() for item in insights)
    assert len({item.code for item in insights}) == len(insights)
