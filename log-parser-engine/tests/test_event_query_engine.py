
import pytest
from datetime import datetime, timedelta, timezone

from log_parser_engine.models import (
    EventFilter,
    EventQuery,
    EventSort,
    LogSeverity,
    LogSourceType,
)
from log_parser_engine.storage import InMemoryEventStore
from log_parser_engine.storage.options import EventStoreOptions


@pytest.fixture
def populated_store() -> InMemoryEventStore:
    """A store pre-populated with a variety of events."""
    store = InMemoryEventStore(EventStoreOptions(max_events=20, indexed_fields=("severity", "host", "tags")))
    now = datetime.now(timezone.utc)
    
    # Total 10 events
    store.add(LogEvent(timestamp=now-timedelta(minutes=9), source_type=LogSourceType.FILE, message="trace event", severity=LogSeverity.TRACE, host="host1", tags=["t1"]))
    store.add(LogEvent(timestamp=now-timedelta(minutes=8), source_type=LogSourceType.SYSLOG, message="debug event", severity=LogSeverity.DEBUG, host="host1", tags=["t1", "t2"]))
    store.add(LogEvent(timestamp=now-timedelta(minutes=7), source_type=LogSourceType.FILE, message="info event 1", severity=LogSeverity.INFO, host="host2", tags=["t2"]))
    store.add(LogEvent(timestamp=now-timedelta(minutes=6), source_type=LogSourceType.FILE, message="info event 2", severity=LogSeverity.INFO, host="host2", tags=["t3"]))
    store.add(LogEvent(timestamp=now-timedelta(minutes=5), source_type=LogSourceType.HTTP, message="warning event", severity=LogSeverity.WARNING, host="host1", tags=["t1", "t3"]))
    store.add(LogEvent(timestamp=now-timedelta(minutes=4), source_type=LogSourceType.FILE, message="error event 1", severity=LogSeverity.ERROR, host="host2", attributes={"http": {"status": 500}}))
    store.add(LogEvent(timestamp=now-timedelta(minutes=3), source_type=LogSourceType.FILE, message="error event 2", severity=LogSeverity.ERROR, host="host2", attributes={"http": {"status": 503}}))
    store.add(LogEvent(timestamp=now-timedelta(minutes=2), source_type=LogSourceType.DATABASE, message="critical event", severity=LogSeverity.CRITICAL, host="host3", tags=["t4"]))
    store.add(LogEvent(timestamp=now-timedelta(minutes=1), source_type=LogSourceType.FILE, message="unknown event", severity=LogSeverity.UNKNOWN, host="host3"))
    store.add(LogEvent(timestamp=now, source_type=LogSourceType.FILE, message="current info event", severity=LogSeverity.INFO, host="host1"))
    
    return store

def test_empty_query(populated_store: InMemoryEventStore):
    """Tests that an empty query returns all events in default order."""
    result = populated_store.query()
    assert result.page.total == 10
    assert result.page.returned == 10
    assert result.events[0].event.message == "current info event" # Default sort is timestamp desc

def test_filter_by_severity(populated_store: InMemoryEventStore):
    """Tests filtering by one or more severities."""
    query = EventQuery(filter=EventFilter(severities=(LogSeverity.ERROR, LogSeverity.CRITICAL)))
    result = populated_store.query(query)
    assert result.page.total == 3
    assert all(e.severity in (LogSeverity.ERROR, LogSeverity.CRITICAL) for e in result.events)

def test_filter_by_time_range(populated_store: InMemoryEventStore):
    """Tests filtering by a time range."""
    now = datetime.now(timezone.utc)
    query = EventQuery(filter=EventFilter(
        start_time=now - timedelta(minutes=4, seconds=30),
        end_time=now - timedelta(minutes=2, seconds=30)
    ))
    result = populated_store.query(query)
    assert result.page.total == 2
    assert "error event 1" in result.events[1].event.message
    assert "error event 2" in result.events[0].event.message

def test_filter_by_tags(populated_store: InMemoryEventStore):
    """Tests filtering by tags (any and all)."""
    # Any t1
    res1 = populated_store.query(EventQuery(filter=EventFilter(tags_any=("t1",))))
    assert res1.page.total == 3
    
    # All t1 and t2
    res2 = populated_store.query(EventQuery(filter=EventFilter(tags_all=("t1", "t2"))))
    assert res2.page.total == 1
    assert res2.events[0].event.message == "debug event"

def test_filter_by_attribute(populated_store: InMemoryEventStore):
    """Tests filtering by attribute existence and value."""
    # Exists
    res1 = populated_store.query(EventQuery(filter=EventFilter(attribute_exists=("http.status",))))
    assert res1.page.total == 2
    
    # Equals
    res2 = populated_store.query(EventQuery(filter=EventFilter(attribute_equals={"http.status": 503})))
    assert res2.page.total == 1
    assert res2.events[0].event.message == "error event 2"

def test_sorting(populated_store: InMemoryEventStore):
    """Tests different sort orders."""
    # Sort by severity ascending
    query = EventQuery(sort=(EventSort(field="severity", direction="asc"),))
    result = populated_store.query(query)
    assert result.events[0].severity == LogSeverity.TRACE
    assert result.events[-1].severity == LogSeverity.UNKNOWN
    
    # Sort by host descending
    query = EventQuery(sort=(EventSort(field="host", direction="desc"),))
    result = populated_store.query(query)
    assert result.events[0].event.host == "host3"

def test_pagination(populated_store: InMemoryEventStore):
    """Tests pagination (offset and limit)."""
    # First page
    query1 = EventQuery(limit=4)
    res1 = populated_store.query(query1)
    assert res1.page.returned == 4
    assert res1.page.has_more is True
    assert res1.page.next_offset == 4

    # Second page
    query2 = EventQuery(limit=4, offset=4)
    res2 = populated_store.query(query2)
    assert res2.page.returned == 4
    assert res2.page.has_more is True
    assert res2.page.next_offset == 8
    
    # Last page
    query3 = EventQuery(limit=4, offset=8)
    res3 = populated_store.query(query3)
    assert res3.page.returned == 2
    assert res3.page.has_more is False
    assert res3.page.next_offset is None

def test_facets(populated_store: InMemoryEventStore):
    """Tests facet calculation."""
    query = EventQuery(include_facets=True, facet_fields=("severity", "host", "tags"))
    result = populated_store.query(query)

    assert "severity" in result.facets
    assert "host" in result.facets
    assert "tags" in result.facets
    
    # Check severity facet - should be sorted by count desc
    severity_facet = result.facets["severity"]
    assert severity_facet[0].value == "INFO"
    assert severity_facet[0].count == 3
    assert severity_facet[1].value == "ERROR"
    assert severity_facet[1].count == 2
    
    # Check host facet
    host_facet = result.facets["host"]
    assert host_facet[0].value == "host1"
    assert host_facet[0].count == 4

    # Check tags facet
    tags_facet = result.facets["tags"]
    assert tags_facet[0].value == "t1"
    assert tags_facet[0].count == 3
