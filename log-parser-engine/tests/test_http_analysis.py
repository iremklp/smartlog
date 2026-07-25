from __future__ import annotations

from datetime import datetime, timedelta, timezone

from log_parser_engine.analysis.http_analysis import analyze_http
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
        "message": f"event {index}",
        "raw_message": f"event {index}",
        "service": "api",
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


def test_http_status_semantics_and_non_http_exclusion() -> None:
    events = (
        make_event(0, http_status=101, http_method="GET", http_path="/stream"),
        make_event(1, http_status=200, http_method="GET", http_path="/ok"),
        make_event(2, http_status=302, http_method="GET", http_path="/redirect"),
        make_event(3, http_status=404, http_method="GET", http_path="/missing"),
        make_event(4, http_status=503, http_method="POST", http_path="/broken"),
        make_event(5, http_method="GET", http_path="/unknown"),
        make_event(
            6,
            source_type=LogSourceType.APPLICATION,
            service=None,
        ),
    )
    result = analyze_http(events, AnalysisRequest())
    assert result.http_event_count == 6
    assert result.events_with_status == 5
    assert result.informational_count == 1
    assert result.success_count == 1
    assert result.redirect_count == 1
    assert result.client_error_count == 1
    assert result.server_error_count == 1
    assert result.unknown_status_count == 1
    assert result.non_error_count == 3
    assert result.total_error_rate == 2 / 6


def test_endpoint_normalization_rankings_and_latency() -> None:
    events = (
        make_event(
            0,
            http_status=200,
            http_method="get",
            http_path="/api/items/?page=1",
            duration_ms=10,
        ),
        make_event(
            1,
            http_status=503,
            http_method="GET",
            http_path="https://example.invalid/api/items/#fragment",
            duration_ms=100,
        ),
        make_event(
            2,
            http_status=500,
            http_method="POST",
            http_path="/other",
            duration_ms=200,
            service="worker",
        ),
    )
    result = analyze_http(
        events,
        AnalysisRequest(top_n=10, time_bucket_seconds=60),
        options=AnalysisOptions(
            minimum_endpoint_requests_for_rate=1,
            minimum_endpoint_latency_samples=1,
        ),
    )
    assert result.endpoint_distribution.items[0].key == "/api/items"
    assert result.endpoint_distribution.items[0].count == 2
    assert result.highest_error_endpoints[0].endpoint == "/other"
    api_items = next(
        item for item in result.slowest_endpoints if item.endpoint == "/api/items"
    )
    assert api_items.request_count == 2
    assert api_items.average_duration_ms == 55
    assert api_items.p95_duration_ms == 100
    assert api_items.methods == ("GET",)
    assert result.timeline is not None


def test_status_breakdowns_are_stable_and_include_unknown() -> None:
    events = (
        make_event(0, http_method="GET", http_status=200, http_path="/a"),
        make_event(1, http_method="GET", http_path="/a"),
        make_event(2, http_method="POST", http_status=500, http_path="/b"),
    )
    result = analyze_http(events, AnalysisRequest(top_n=10))
    assert [item.key for item in result.status_by_method] == ["GET", "POST"]
    assert result.status_by_method[0].unknown_status_count == 1
    assert result.status_by_method[1].server_error_count == 1


def test_explicit_http_method_field_drives_all_method_outputs_consistently() -> None:
    events = (
        make_event(
            0,
            http_status=200,
            http_path="/custom",
            attributes={"custom": {"method": "PATCH"}},
        ),
    )

    result = analyze_http(
        events,
        AnalysisRequest(method_field="custom.method"),
    )

    assert result.events_with_method == 1
    assert result.method_distribution.items[0].key == "PATCH"
    assert result.status_by_method[0].key == "PATCH"


def test_missing_status_warning_is_cautious_and_bounded() -> None:
    result = analyze_http(
        (
            make_event(0, http_method="GET"),
            make_event(1, http_method="POST"),
            make_event(2, http_status=200),
        ),
        AnalysisRequest(),
    )
    assert result.warnings == ("MISSING_HTTP_STATUS_DATA",)


def test_empty_http_analysis_has_consistent_distributions() -> None:
    result = analyze_http((), AnalysisRequest())
    assert result.http_event_count == 0
    assert result.status_code_distribution.total_count == 0
    assert result.endpoint_distribution.items == ()
