from datetime import datetime, timezone

from log_parser_engine.models import (
    LogEvent,
    LogSourceType,
    ParseResult,
    ParseStatus,
)


def test_parse_result_tracks_success_and_errors() -> None:
    event = LogEvent(
        timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        source_type=LogSourceType.application,
        message="ok",
        raw_message="ok",
    )
    result = ParseResult(status=ParseStatus.success, events=[event], errors=[])

    assert result.status == ParseStatus.success
    assert len(result.events) == 1
    assert result.errors == []
    assert result.model_dump(mode="json")["status"] == "success"


def test_parse_result_defaults_to_empty_lists() -> None:
    result = ParseResult(status=ParseStatus.partial)

    assert result.events == []
    assert result.errors == []
    assert result.status == ParseStatus.partial
