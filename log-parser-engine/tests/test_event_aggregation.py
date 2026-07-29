from datetime import datetime, timezone

import pytest

from log_parser_engine.models import (
    EventAggregationRequest,
    EventQuery,
    LogEvent,
    LogSeverity,
    LogSourceType,
)
from log_parser_engine.storage import InMemoryEventStore
from log_parser_engine.storage.options import EventStoreOptions


def _event(
    message: str,
    *,
    now: datetime,
    source_type: LogSourceType,
    severity: LogSeverity,
    duration_ms: float,
) -> LogEvent:
    return LogEvent(
        timestamp=now,
        source_type=source_type,
        message=message,
        raw_message=message,
        severity=severity,
        duration_ms=duration_ms,
    )


@pytest.fixture
def store_for_agg() -> InMemoryEventStore:
    """Return a store populated with valid canonical events."""

    store = InMemoryEventStore(EventStoreOptions(max_events=20))
    now = datetime.now(timezone.utc)
    events = (
        _event(
            "m1",
            now=now,
            source_type=LogSourceType.FILE,
            severity=LogSeverity.INFO,
            duration_ms=100,
        ),
        _event(
            "m2",
            now=now,
            source_type=LogSourceType.FILE,
            severity=LogSeverity.INFO,
            duration_ms=150,
        ),
        _event(
            "m3",
            now=now,
            source_type=LogSourceType.FILE,
            severity=LogSeverity.WARNING,
            duration_ms=200,
        ),
        _event(
            "m4",
            now=now,
            source_type=LogSourceType.HTTP,
            severity=LogSeverity.WARNING,
            duration_ms=250,
        ),
        _event(
            "m5",
            now=now,
            source_type=LogSourceType.HTTP,
            severity=LogSeverity.ERROR,
            duration_ms=300,
        ),
    )
    store.add_many(events)
    return store


def test_aggregation_count_by_severity(
    store_for_agg: InMemoryEventStore,
) -> None:
    """Count events grouped by severity."""

    agg = EventAggregationRequest(group_by="severity", metric="count")
    result = store_for_agg.query(EventQuery(aggregation=agg))
    agg_result = result.aggregation

    assert agg_result is not None
    buckets = {bucket.group_value: bucket for bucket in agg_result.buckets}
    assert len(buckets) == 3
    assert buckets[LogSeverity.INFO.value].metric_value == 2
    assert buckets[LogSeverity.WARNING.value].metric_value == 2
    assert buckets[LogSeverity.ERROR.value].metric_value == 1


def test_aggregation_avg_duration(
    store_for_agg: InMemoryEventStore,
) -> None:
    """Average duration grouped by source type."""

    agg = EventAggregationRequest(
        group_by="source_type",
        metric="average_duration_ms",
    )
    result = store_for_agg.query(EventQuery(aggregation=agg))
    agg_result = result.aggregation

    assert agg_result is not None
    buckets = {bucket.group_value: bucket for bucket in agg_result.buckets}
    assert len(buckets) == 2
    assert buckets[LogSourceType.FILE.value].metric_value == 150
    assert buckets[LogSourceType.HTTP.value].metric_value == 275
    assert buckets[LogSourceType.HTTP.value].sample_count == 2
    assert buckets[LogSourceType.FILE.value].event_count == 3


def test_aggregation_sum_duration(
    store_for_agg: InMemoryEventStore,
) -> None:
    """Sum duration grouped by severity."""

    agg = EventAggregationRequest(
        group_by="severity",
        metric="sum_duration_ms",
    )
    result = store_for_agg.query(EventQuery(aggregation=agg))
    agg_result = result.aggregation

    assert agg_result is not None
    buckets = {bucket.group_value: bucket for bucket in agg_result.buckets}
    assert buckets[LogSeverity.INFO.value].metric_value == 250
    assert buckets[LogSeverity.WARNING.value].metric_value == 450
    assert buckets[LogSeverity.ERROR.value].metric_value == 300
