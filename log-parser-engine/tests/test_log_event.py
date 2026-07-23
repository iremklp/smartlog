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
