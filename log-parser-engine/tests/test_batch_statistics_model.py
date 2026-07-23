from __future__ import annotations

from datetime import datetime, timezone

from log_parser_engine.models import BatchParseStatistics


def test_batch_statistics_rates() -> None:
    stats = BatchParseStatistics(
        records_seen=3,
        records_attempted=2,
        records_succeeded=1,
        records_failed=1,
    )
    assert stats.success_rate == 0.5
    assert stats.error_rate == 0.5


def test_batch_statistics_timestamps_validate() -> None:
    stats = BatchParseStatistics(
        earliest_event_timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        latest_event_timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
    )
    assert stats.earliest_event_timestamp is not None
