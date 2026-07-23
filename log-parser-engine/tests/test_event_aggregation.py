
import pytest
from datetime import datetime, timedelta, timezone

from log_parser_engine.models import (
    EventAggregationRequest,
    EventQuery,
    LogSeverity,
    LogSourceType,
    LogEvent,
)
from log_parser_engine.storage import InMemoryEventStore
from log_parser_engine.storage.options import EventStoreOptions

@pytest.fixture
def store_for_agg() -> InMemoryEventStore:
    """A store pre-populated with events for aggregation tests."""
    store = InMemoryEventStore(EventStoreOptions(max_events=20))
    now = datetime.now(timezone.utc)
    
    store.add(LogEvent(timestamp=now, source_type=LogSourceType.FILE, message="m1", severity=LogSeverity.INFO, duration_ms=100))
    store.add(LogEvent(timestamp=now, source_type=LogSourceType.FILE, message="m2", severity=LogSeverity.INFO, duration_ms=150))
    store.add(LogEvent(timestamp=now, source_type=LogSourceType.FILE, message="m3", severity=LogSeverity.WARNING, duration_ms=200))
    store.add(LogEvent(timestamp=now, source_type=LogSourceType.HTTP, message="m4", severity=LogSeverity.WARNING, duration_ms=250))
    store.add(LogEvent(timestamp=now, source_type=LogSourceType.HTTP, message="m5", severity=LogSeverity.ERROR, duration_ms=300))
    
    return store

def test_aggregation_count_by_severity(store_for_agg: InMemoryEventStore):
    """Tests count aggregation grouped by severity."""
    agg = EventAggregationRequest(group_by="severity", metric="count")
    query = EventQuery(aggregation=agg)
    
    result = store_for_agg.query(query)
    agg_result = result.aggregation
    
    assert agg_result is not None
    buckets = {b.group_value: b for b in agg_result.buckets}
    
    assert len(buckets) == 3
    assert buckets[LogSeverity.INFO.value].metric_value == 2
    assert buckets[LogSeverity.WARNING.value].metric_value == 2
    assert buckets[LogSeverity.ERROR.value].metric_value == 1

def test_aggregation_avg_duration(store_for_agg: InMemoryEventStore):
    """Tests average duration aggregation grouped by source_type."""
    agg = EventAggregationRequest(group_by="source_type", metric="average_duration_ms")
    query = EventQuery(aggregation=agg)
    
    result = store_for_agg.query(query)
    agg_result = result.aggregation
    
    assert agg_result is not None
    buckets = {b.group_value: b for b in agg_result.buckets}

    assert len(buckets) == 2
    assert buckets[LogSourceType.FILE.value].metric_value == (100 + 150 + 200) / 3
    assert buckets[LogSourceType.HTTP.value].metric_value == (250 + 300) / 2
    assert buckets[LogSourceType.HTTP.value].sample_count == 2
    assert buckets[LogSourceType.FILE.value].event_count == 3


def test_aggregation_sum_duration(store_for_agg: InMemoryEventStore):
    """Tests sum of duration aggregation."""
    agg = EventAggregationRequest(group_by="severity", metric="sum_duration_ms")
    query = EventQuery(aggregation=agg)
    
    result = store_for_agg.query(query)
    agg_result = result.aggregation
    
    assert agg_result is not None
    buckets = {b.group_value: b for b in agg_result.buckets}

    assert buckets[LogSeverity.INFO.value].metric_value == 100 + 150
    assert buckets[LogSeverity.WARNING.value].metric_value == 200 + 250
    assert buckets[LogSeverity.ERROR.value].metric_value == 300
