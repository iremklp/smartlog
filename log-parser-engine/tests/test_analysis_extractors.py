from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from log_parser_engine.analysis.extractors import (
    extract_duration_ms,
    extract_numeric_value,
    get_http_method,
    get_http_path,
    get_http_status,
    get_parser_name,
    is_http_event,
    normalize_endpoint,
)
from log_parser_engine.analysis.validation import resolve_attribute_path
from log_parser_engine.models.enums import LogSeverity, LogSourceType
from log_parser_engine.models.log_event import LogEvent
from log_parser_engine.models.stored_event import StoredEvent


def make_event(**updates: object) -> StoredEvent:
    event_values: dict[str, object] = {
        "timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "source_type": LogSourceType.APPLICATION,
        "severity": LogSeverity.INFO,
        "message": "synthetic event",
        "raw_message": "synthetic event",
    }
    event_values.update(updates)
    event = LogEvent(**event_values)
    return StoredEvent(
        id="evt-1",
        event=event,
        inserted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        sequence=1,
        content_hash="a" * 64,
        estimated_size_bytes=100,
    )


def test_direct_duration_has_priority() -> None:
    event = make_event(
        duration_ms=12.5,
        attributes={"duration_ms": 99, "request_time": 2},
    )
    extracted = extract_duration_ms(event)
    assert extracted.value == 12.5
    assert extracted.field == "duration_ms"
    assert extracted.valid


def test_duration_units_are_converted_to_milliseconds() -> None:
    milliseconds = make_event(attributes={"duration_ms": 8})
    seconds = make_event(attributes={"request_time": Decimal("1.25")})
    microseconds = make_event(attributes={"duration_us": 2_500})
    assert extract_duration_ms(milliseconds).value == 8
    assert extract_duration_ms(seconds).value == 1_250
    assert extract_duration_ms(microseconds).value == 2.5


def test_nested_explicit_duration_fields_preserve_leaf_units() -> None:
    event = make_event(
        attributes={
            "custom": {"duration_us": 2_500},
            "nginx": {"request_time": 1.2},
        }
    )

    microseconds = extract_duration_ms(
        event,
        explicit_field="custom.duration_us",
    )
    seconds = extract_duration_ms(
        event,
        explicit_field="nginx.request_time",
    )

    assert microseconds.value == 2.5
    assert seconds.value == 1_200


def test_numeric_string_depends_on_strict_mode() -> None:
    event = make_event(attributes={"latency_ms": " 42.5 "})
    assert extract_duration_ms(event, strict=True).value is None
    assert extract_duration_ms(event, strict=False).value == 42.5


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), -1])
def test_invalid_duration_is_reported(value: object) -> None:
    event = make_event(attributes={"latency_ms": value})
    result = extract_duration_ms(event)
    assert result.found
    assert not result.valid
    assert result.value is None


@pytest.mark.parametrize(
    "value",
    [10**400, Decimal("1e1000000")],
    ids=("huge-int", "huge-decimal"),
)
def test_overflowing_duration_is_safely_reported_as_invalid(value: object) -> None:
    event = make_event(attributes={"latency_ms": value})

    result = extract_duration_ms(event)

    assert result.found
    assert not result.valid
    assert result.value is None


def test_duration_unit_conversion_overflow_is_safely_invalid() -> None:
    event = make_event(attributes={"request_time": 1e308})

    result = extract_duration_ms(event)

    assert result.found
    assert not result.valid
    assert result.reason == "unit_conversion_overflow"


def test_explicit_numeric_attribute_path_precedes_candidates() -> None:
    event = make_event(attributes={"custom": {"latency": 7}, "latency_ms": 99})
    result = extract_numeric_value(
        event.event,
        explicit_field="custom.latency",
        candidates=("latency_ms",),
        max_depth=10,
    )
    assert result.value == 7
    assert result.field == "custom.latency"


def test_safe_attribute_resolver_rejects_dunder_and_lists() -> None:
    attributes = {"safe": {"value": 1}, "items": [{"value": 2}]}
    assert resolve_attribute_path(attributes, "safe.value") == (True, 1)
    assert resolve_attribute_path(attributes, "__class__") == (False, None)
    assert resolve_attribute_path(attributes, "items.0.value") == (False, None)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("200", 200),
        (503, 503),
        ("200 OK", None),
        ("99", None),
        ("999", None),
        (True, None),
    ],
)
def test_http_status_is_strict(raw: object, expected: int | None) -> None:
    event = make_event(attributes={"status_code": raw})
    assert get_http_status(event) == expected


def test_http_fields_and_parser_name_use_safe_fallbacks() -> None:
    event = make_event(
        attributes={
            "http": {"method": "get", "status_code": "204"},
            "url": {"path": "/api/items?debug=true"},
            "parser_name": "json_log",
        }
    )
    assert get_http_method(event) == "GET"
    assert get_http_status(event) == 204
    assert get_http_path(event) == "/api/items"
    assert get_parser_name(event) == "json_log"
    assert is_http_event(event)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://example.invalid/a/b?q=1#x", "/a/b"),
        ("/api/users/?page=2", "/api/users"),
        ("/", "/"),
        ("relative/path", "/relative/path"),
        ("   ", None),
    ],
)
def test_endpoint_normalization(raw: str, expected: str | None) -> None:
    assert normalize_endpoint(raw) == expected


def test_route_template_has_priority_over_raw_path() -> None:
    event = make_event(
        http_path="/users/123?x=1",
        attributes={"http": {"route": "/users/{id}/"}},
    )
    assert get_http_path(event) == "/users/{id}"


def test_extractors_do_not_mutate_event() -> None:
    event = make_event(attributes={"latency_ms": 5, "status": "200"})
    before = event.model_dump()
    extract_duration_ms(event)
    get_http_status(event)
    get_http_path(event)
    assert event.model_dump() == before
