from datetime import datetime, timedelta, timezone
from typing import Literal

import pytest

from log_parser_engine.exceptions import EventPaginationError
from log_parser_engine.models import (
    EventAggregationRequest,
    EventFilter,
    EventQuery,
    EventSort,
    LogEvent,
    LogSeverity,
    LogSourceType,
)
from log_parser_engine.storage import InMemoryEventStore
from log_parser_engine.storage.options import EventStoreOptions


def _event(
    message: str,
    *,
    timestamp: datetime,
    source_type: LogSourceType = LogSourceType.FILE,
    severity: LogSeverity = LogSeverity.INFO,
    host: str | None,
    tags: tuple[str, ...] = (),
    attributes: dict[str, object] | None = None,
    duration_ms: float | None = None,
) -> LogEvent:
    return LogEvent(
        timestamp=timestamp,
        source_type=source_type,
        message=message,
        raw_message=message,
        severity=severity,
        host=host,
        tags=list(tags),
        attributes=attributes or {},
        duration_ms=duration_ms,
    )


@pytest.fixture
def populated_store() -> InMemoryEventStore:
    """Return a store populated with varied canonical events."""

    store = InMemoryEventStore(
        EventStoreOptions(
            max_events=20,
            indexed_fields=("severity", "host", "tags"),
        )
    )
    now = datetime.now(timezone.utc)
    events = (
        _event(
            "trace event",
            timestamp=now - timedelta(minutes=9),
            severity=LogSeverity.TRACE,
            host="host1",
            tags=("t1",),
        ),
        _event(
            "debug event",
            timestamp=now - timedelta(minutes=8),
            source_type=LogSourceType.SYSLOG,
            severity=LogSeverity.DEBUG,
            host="host1",
            tags=("t1", "t2"),
        ),
        _event(
            "info event 1",
            timestamp=now - timedelta(minutes=7),
            host="host2",
            tags=("t2",),
        ),
        _event(
            "info event 2",
            timestamp=now - timedelta(minutes=6),
            host="host2",
            tags=("t3",),
        ),
        _event(
            "warning event",
            timestamp=now - timedelta(minutes=5),
            source_type=LogSourceType.HTTP,
            severity=LogSeverity.WARNING,
            host="host1",
            tags=("t1", "t3"),
        ),
        _event(
            "error event 1",
            timestamp=now - timedelta(minutes=4),
            severity=LogSeverity.ERROR,
            host="host2",
            attributes={"http": {"status": 500}},
        ),
        _event(
            "error event 2",
            timestamp=now - timedelta(minutes=3),
            severity=LogSeverity.ERROR,
            host="host2",
            attributes={"http": {"status": 503}},
        ),
        _event(
            "critical event",
            timestamp=now - timedelta(minutes=2),
            source_type=LogSourceType.DATABASE,
            severity=LogSeverity.CRITICAL,
            host="host3",
            tags=("t4",),
        ),
        _event(
            "unknown event",
            timestamp=now - timedelta(minutes=1),
            severity=LogSeverity.UNKNOWN,
            host="host3",
        ),
        _event(
            "current info event",
            timestamp=now,
            host="host1",
        ),
    )
    store.add_many(events)
    return store


def test_empty_query(populated_store: InMemoryEventStore) -> None:
    """An empty query returns all events in default order."""

    result = populated_store.query()
    assert result.page.total == 10
    assert result.page.returned == 10
    assert result.events[0].event.message == "current info event"


def test_filter_by_severity(populated_store: InMemoryEventStore) -> None:
    """Filter by one or more severities."""

    query = EventQuery(
        filter=EventFilter(
            severities=(LogSeverity.ERROR, LogSeverity.CRITICAL)
        )
    )
    result = populated_store.query(query)
    assert result.page.total == 3
    assert all(
        event.severity in (LogSeverity.ERROR, LogSeverity.CRITICAL)
        for event in result.events
    )


def test_filter_by_time_range(populated_store: InMemoryEventStore) -> None:
    """Filter by inclusive start and exclusive end timestamps."""

    timestamps = [event.timestamp for event in populated_store.snapshot_events()]
    newest = max(timestamps)
    query = EventQuery(
        filter=EventFilter(
            start_time=newest - timedelta(minutes=4, seconds=30),
            end_time=newest - timedelta(minutes=2, seconds=30),
        )
    )
    result = populated_store.query(query)
    assert result.page.total == 2
    assert result.events[0].event.message == "error event 2"
    assert result.events[1].event.message == "error event 1"


def test_filter_by_tags(populated_store: InMemoryEventStore) -> None:
    """Apply any/all tag semantics."""

    any_tag = populated_store.query(
        EventQuery(filter=EventFilter(tags_any=("t1",)))
    )
    assert any_tag.page.total == 3

    all_tags = populated_store.query(
        EventQuery(filter=EventFilter(tags_all=("t1", "t2")))
    )
    assert all_tags.page.total == 1
    assert all_tags.events[0].event.message == "debug event"


def test_filter_by_attribute(populated_store: InMemoryEventStore) -> None:
    """Filter by safe nested attribute existence and equality."""

    existing = populated_store.query(
        EventQuery(
            filter=EventFilter(attribute_exists=("http.status",))
        )
    )
    assert existing.page.total == 2

    matching = populated_store.query(
        EventQuery(
            filter=EventFilter(
                attribute_equals={"http.status": 503}
            )
        )
    )
    assert matching.page.total == 1
    assert matching.events[0].event.message == "error event 2"


def test_sorting(populated_store: InMemoryEventStore) -> None:
    """Apply semantic severity and regular field sorting."""

    severity_query = EventQuery(
        sort=(EventSort(field="severity", direction="asc"),)
    )
    severity_result = populated_store.query(severity_query)
    assert severity_result.events[0].severity == LogSeverity.TRACE
    assert severity_result.events[-1].severity == LogSeverity.UNKNOWN

    host_query = EventQuery(
        sort=(EventSort(field="host", direction="desc"),)
    )
    host_result = populated_store.query(host_query)
    assert host_result.events[0].event.host == "host3"


def test_pagination(populated_store: InMemoryEventStore) -> None:
    """Return deterministic offset pages."""

    first = populated_store.query(EventQuery(limit=4))
    assert first.page.returned == 4
    assert first.page.has_more is True
    assert first.page.next_offset == 4

    second = populated_store.query(EventQuery(limit=4, offset=4))
    assert second.page.returned == 4
    assert second.page.has_more is True
    assert second.page.next_offset == 8

    last = populated_store.query(EventQuery(limit=4, offset=8))
    assert last.page.returned == 2
    assert last.page.has_more is False
    assert last.page.next_offset is None


def test_facets(populated_store: InMemoryEventStore) -> None:
    """Calculate deterministic facets for the filtered snapshot."""

    query = EventQuery(
        include_facets=True,
        facet_fields=("severity", "host", "tags"),
    )
    result = populated_store.query(query)

    assert "severity" in result.facets
    assert "host" in result.facets
    assert "tags" in result.facets

    severity_facet = result.facets["severity"]
    assert severity_facet[0].value == LogSeverity.INFO.value
    assert severity_facet[0].count == 3
    assert severity_facet[1].value == LogSeverity.ERROR.value
    assert severity_facet[1].count == 2

    host_facet = result.facets["host"]
    assert host_facet[0].value == "host1"
    assert host_facet[0].count == 4

    tags_facet = result.facets["tags"]
    assert tags_facet[0].value == "t1"
    assert tags_facet[0].count == 3


def test_unconfigured_index_falls_back_to_full_scan() -> None:
    """A valid filter never becomes empty because its index is disabled."""

    store = InMemoryEventStore(
        EventStoreOptions(
            max_events=10,
            indexed_fields=("severity",),
        )
    )
    now = datetime.now(timezone.utc)
    store.add_many(
        (
            _event("one", timestamp=now, host="host1"),
            _event("two", timestamp=now, host="host2"),
        )
    )

    result = store.query(
        EventQuery(filter=EventFilter(hosts=("host2",)))
    )

    assert result.page.total == 1
    assert result.events[0].event.message == "two"
    assert result.index_used is False


def test_parser_name_filter_facet_and_aggregation_use_canonical_extractor(
) -> None:
    """Parser metadata behaves consistently across all query surfaces."""

    store = InMemoryEventStore(EventStoreOptions(max_events=10))
    now = datetime.now(timezone.utc)
    store.add_many(
        (
            _event(
                "json one",
                timestamp=now,
                host="host1",
                attributes={"parser_name": "json"},
            ),
            _event(
                "json two",
                timestamp=now,
                host="host1",
                attributes={"parser_name": "json"},
            ),
            _event(
                "redis",
                timestamp=now,
                host="host1",
                attributes={"parser_name": "redis"},
            ),
        )
    )

    query = EventQuery(
        filter=EventFilter(parser_names=("json",)),
        include_facets=True,
        facet_fields=("parser_name",),
        aggregation=EventAggregationRequest(
            group_by="parser_name",
            metric="count",
        ),
    )
    result = store.query(query)

    assert result.page.total == 2
    assert result.index_used is True
    assert result.facets["parser_name"][0].value == "json"
    assert result.facets["parser_name"][0].count == 2
    assert result.aggregation is not None
    assert result.aggregation.buckets[0].group_value == "json"
    assert result.aggregation.buckets[0].metric_value == 2


@pytest.mark.parametrize("direction", ["asc", "desc"])
def test_optional_sort_values_are_always_last(
    direction: Literal["asc", "desc"],
) -> None:
    """Optional sort values do not crash and remain last in either direction."""

    store = InMemoryEventStore(EventStoreOptions(max_events=10))
    now = datetime.now(timezone.utc)
    store.add_many(
        (
            _event("missing", timestamp=now, host=None),
            _event("alpha", timestamp=now, host="alpha"),
            _event("zulu", timestamp=now, host="zulu"),
        )
    )

    result = store.query(
        EventQuery(
            sort=(EventSort(field="host", direction=direction),)
        )
    )

    assert result.events[-1].event.host is None


def test_severity_sort_includes_notice_and_fatal() -> None:
    """Semantic severity order includes every canonical severity."""

    store = InMemoryEventStore(EventStoreOptions(max_events=10))
    now = datetime.now(timezone.utc)
    severities = (
        LogSeverity.FATAL,
        LogSeverity.WARNING,
        LogSeverity.NOTICE,
        LogSeverity.INFO,
        LogSeverity.UNKNOWN,
    )
    store.add_many(
        tuple(
            _event(
                severity.value,
                timestamp=now,
                severity=severity,
                host="host1",
            )
            for severity in severities
        )
    )

    result = store.query(
        EventQuery(
            sort=(EventSort(field="severity", direction="asc"),)
        )
    )

    assert [event.severity for event in result.events] == [
        LogSeverity.INFO,
        LogSeverity.NOTICE,
        LogSeverity.WARNING,
        LogSeverity.FATAL,
        LogSeverity.UNKNOWN,
    ]


def test_query_limit_is_bounded_by_store_options() -> None:
    """Runtime store limits cannot be bypassed by a valid query model."""

    store = InMemoryEventStore(
        EventStoreOptions(
            max_events=10,
            default_page_size=2,
            max_page_size=2,
            max_query_limit=2,
        )
    )

    with pytest.raises(EventPaginationError, match="configured maximum"):
        store.query(EventQuery(limit=3))


def test_empty_aggregation_is_distinct_from_no_aggregation() -> None:
    """A requested aggregation returns an explicit empty result."""

    store = InMemoryEventStore()
    result = store.query(
        EventQuery(
            aggregation=EventAggregationRequest(
                group_by="severity",
                metric="count",
            )
        )
    )

    assert result.aggregation is not None
    assert result.aggregation.buckets == ()


def test_time_bucket_aggregation_is_utc_aligned_and_chronological() -> None:
    """Fixed-duration buckets align to UTC epoch boundaries."""

    store = InMemoryEventStore(EventStoreOptions(max_events=10))
    base = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)
    store.add_many(
        (
            _event(
                "late",
                timestamp=base + timedelta(seconds=75),
                host="host1",
            ),
            _event(
                "early one",
                timestamp=base + timedelta(seconds=5),
                host="host1",
            ),
            _event(
                "early two",
                timestamp=base + timedelta(seconds=59),
                host="host1",
            ),
        )
    )

    result = store.query(
        EventQuery(
            aggregation=EventAggregationRequest(
                group_by="time_bucket",
                metric="count",
                time_bucket_seconds=60,
            )
        )
    )

    assert result.aggregation is not None
    buckets = result.aggregation.buckets
    assert [bucket.metric_value for bucket in buckets] == [2, 1]
    assert buckets[0].bucket_start_time == base
    assert buckets[0].bucket_end_time == base + timedelta(seconds=60)
    assert buckets[1].bucket_start_time == base + timedelta(seconds=60)


def test_average_duration_without_samples_is_none() -> None:
    """An empty metric sample set is not reported as a measured zero."""

    store = InMemoryEventStore()
    now = datetime.now(timezone.utc)
    store.add(_event("no duration", timestamp=now, host="host1"))

    result = store.query(
        EventQuery(
            aggregation=EventAggregationRequest(
                group_by="host",
                metric="average_duration_ms",
            )
        )
    )

    assert result.aggregation is not None
    bucket = result.aggregation.buckets[0]
    assert bucket.event_count == 1
    assert bucket.sample_count == 0
    assert bucket.metric_value is None


def test_facet_bucket_count_respects_store_limit() -> None:
    """Facet result cardinality is bounded by immutable store options."""

    store = InMemoryEventStore(
        EventStoreOptions(
            max_events=10,
            max_facet_buckets=2,
        )
    )
    now = datetime.now(timezone.utc)
    store.add_many(
        (
            _event("one", timestamp=now, host="one"),
            _event("two", timestamp=now, host="two"),
            _event("three", timestamp=now, host="three"),
        )
    )

    result = store.query(
        EventQuery(
            include_facets=True,
            facet_fields=("host",),
        )
    )

    assert len(result.facets["host"]) == 2
