from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from log_parser_engine.models import LogEvent, LogSeverity, LogSourceType


def test_log_event_validates_and_serializes() -> None:
    event = LogEvent(
        timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        source_type=LogSourceType.nginx,
        message="  Hello world  ",
        raw_message="2024-01-01 12:00:00 nginx: Hello world",
        tags=[" alpha ", "alpha", "", "beta "],
        http_status=200,
        duration_ms=12.5,
        attributes={"parser": "nginx"},
    )

    assert event.message == "Hello world"
    assert event.tags == ["alpha", "beta"]
    assert event.severity == LogSeverity.unknown
    assert event.ingested_at.tzinfo is not None
    assert event.model_dump(mode="json")["source_type"] == "nginx"
    assert event.model_dump(mode="json")["severity"] == "unknown"


def test_log_event_rejects_naive_timestamp() -> None:
    with pytest.raises(ValidationError):
        LogEvent(
            timestamp=datetime(2024, 1, 1, 12, 0),
            source_type=LogSourceType.application,
            message="hello",
            raw_message="hello",
        )


def test_nested_log_event_collections_are_immutable() -> None:
    event = LogEvent(
        timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        source_type=LogSourceType.nginx,
        message="hello",
        raw_message="hello",
        attributes={"nested": {"values": [1, 2]}},
        tags=["alpha"],
    )

    with pytest.raises(TypeError, match="mutation"):
        event.attributes["new"] = True
    with pytest.raises(TypeError, match="mutation"):
        event.attributes["nested"]["new"] = True
    with pytest.raises(TypeError, match="mutation"):
        event.tags.append("beta")


def test_validated_updates_preserve_identity_and_refreeze_collections() -> None:
    event = LogEvent(
        timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        source_type=LogSourceType.nginx,
        message="original",
        raw_message="original",
        attributes={"nested": {"value": 1}},
        tags=["alpha"],
    )

    updated = event.with_validated_updates(
        {
            "message": "  updated  ",
            "attributes": {"nested": {"value": 2}},
            "tags": ["beta", "beta"],
        }
    )

    assert updated.event_id == event.event_id
    assert updated.ingested_at == event.ingested_at
    assert updated.message == "updated"
    assert updated.attributes["nested"]["value"] == 2
    assert updated.tags == ["beta"]
    assert event.message == "original"
    assert event.attributes["nested"]["value"] == 1
    assert event.tags == ["alpha"]

    with pytest.raises(TypeError, match="mutation"):
        updated.attributes["new"] = True
    with pytest.raises(TypeError, match="mutation"):
        updated.attributes["nested"]["new"] = True
    with pytest.raises(TypeError, match="mutation"):
        updated.tags.append("gamma")


@pytest.mark.parametrize(
    "updates",
    [
        {"message": "   "},
        {"timestamp": datetime(2024, 1, 1, 12, 0)},
        {"http_status": 99},
        {"duration_ms": -0.1},
        {"duration_ms": float("nan")},
        {"duration_ms": float("inf")},
    ],
)
def test_validated_updates_reject_invalid_values(
    updates: dict[str, object],
) -> None:
    event = LogEvent(
        timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        source_type=LogSourceType.nginx,
        message="original",
        raw_message="original",
    )

    with pytest.raises(ValidationError):
        event.with_validated_updates(updates)
