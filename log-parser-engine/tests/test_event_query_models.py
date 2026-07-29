from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from log_parser_engine.models import (
    AggregationBucket,
    EventAggregationRequest,
    EventFilter,
    EventPage,
    EventQuery,
    EventSort,
)


def test_event_filter_defaults():
    """Tests that an empty EventFilter has correct defaults."""
    f = EventFilter()
    assert f.event_ids == tuple()
    assert f.start_time is None
    assert f.severities == tuple()
    assert f.tags_any == tuple()
    assert f.tags_all == tuple()
    assert f.message_contains is None
    assert f.attribute_equals == {}


def test_event_filter_validation():
    """Tests validation rules for EventFilter."""
    now = datetime.now(timezone.utc)

    with pytest.raises(ValidationError, match="start_time cannot be after end_time"):
        EventFilter(start_time=now, end_time=now - timedelta(seconds=1))

    with pytest.raises(ValidationError, match="must be timezone-aware"):
        EventFilter(start_time=datetime.now())

    # Test normalization of string tuples
    f = EventFilter(hosts=(" host2 ", "host1", " host2 "))
    assert f.hosts == ("host1", "host2")


def test_event_filter_rejects_unsafe_non_finite_and_unbounded_attributes():
    with pytest.raises(ValidationError, match="unsafe"):
        EventFilter(attribute_exists=("__class__.name",))

    with pytest.raises(ValidationError, match="finite"):
        EventFilter(attribute_equals={"duration": float("nan")})

    with pytest.raises(ValidationError, match="too many"):
        EventFilter(attribute_equals={f"field_{index}": index for index in range(101)})


def test_event_filter_attribute_mapping_is_immutable():
    event_filter = EventFilter(attribute_equals={"http.status": 500})

    with pytest.raises(TypeError, match="mutation"):
        event_filter.attribute_equals["http.status"] = 200


def test_event_sort_model():
    """Tests the EventSort model."""
    s = EventSort(field="timestamp", direction="desc")
    assert s.field == "timestamp"
    assert s.direction == "desc"

    with pytest.raises(ValidationError):
        EventSort(field="invalid_field", direction="desc")

    with pytest.raises(ValidationError):
        EventSort(field="timestamp", direction="invalid_direction")


def test_event_query_model():
    """Tests the main EventQuery model."""
    q = EventQuery()
    assert isinstance(q.filter, EventFilter)
    assert q.sort == tuple()
    assert q.offset == 0
    assert q.limit is None

    # Test sort validation
    with pytest.raises(
        ValidationError, match="Duplicate sort field 'timestamp' is not allowed"
    ):
        EventQuery(
            sort=(
                EventSort(field="timestamp", direction="desc"),
                EventSort(field="timestamp", direction="asc"),
            )
        )

    with pytest.raises(ValidationError):
        EventQuery(limit=0)

    with pytest.raises(ValidationError):
        EventQuery(facet_fields=("not_a_facet",))


def test_event_aggregation_request_validates_field_combinations() -> None:
    """Aggregation options reject ambiguous or unsupported combinations."""

    request = EventAggregationRequest(
        group_by="time_bucket",
        metric="count",
        time_bucket_seconds=60,
    )
    assert request.time_bucket_seconds == 60

    with pytest.raises(ValidationError, match="required"):
        EventAggregationRequest(group_by="time_bucket", metric="count")

    with pytest.raises(ValidationError, match="only be set"):
        EventAggregationRequest(
            group_by="severity",
            metric="count",
            time_bucket_seconds=60,
        )

    with pytest.raises(ValidationError, match="cannot be grouped"):
        EventAggregationRequest(
            group_by="tag",
            metric="average_duration_ms",
        )


def test_aggregation_bucket_validates_time_bounds() -> None:
    """Time bucket bounds are paired, aware and increasing."""

    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError, match="set together"):
        AggregationBucket(
            group_value="bucket",
            event_count=1,
            metric_value=1,
            bucket_start_time=now,
        )

    with pytest.raises(ValidationError, match="timezone-aware"):
        AggregationBucket(
            group_value="bucket",
            event_count=1,
            metric_value=1,
            bucket_start_time=datetime.now(),
            bucket_end_time=datetime.now() + timedelta(seconds=1),
        )


def test_event_page_model():
    """Tests the EventPage model and its properties."""
    # Test with known total
    page = EventPage(offset=0, limit=10, returned=10, total=25)
    assert page.has_more is True
    assert page.next_offset == 10

    page = EventPage(offset=10, limit=10, returned=10, total=25)
    assert page.has_more is True
    assert page.next_offset == 20

    page = EventPage(offset=20, limit=10, returned=5, total=25)
    assert page.has_more is False
    assert page.next_offset is None

    # Test with unknown total
    page = EventPage(offset=0, limit=10, returned=10, total=None)
    assert page.has_more is True  # We assume more if a full page was returned
    assert page.next_offset == 10

    page = EventPage(offset=10, limit=10, returned=5, total=None)
    assert page.has_more is False
    assert page.next_offset is None

    # Test validation
    with pytest.raises(ValidationError):
        EventPage(offset=-1, limit=10, returned=5, total=20)
    with pytest.raises(ValidationError):
        EventPage(offset=0, limit=10, returned=11, total=20)
    with pytest.raises(ValidationError):
        EventPage(offset=0, limit=10, returned=5, total=4)
    with pytest.raises(ValidationError):
        EventPage(offset=0, limit=0, returned=0, total=0)
