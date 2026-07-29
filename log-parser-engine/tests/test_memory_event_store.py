
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from log_parser_engine.exceptions import (
    DuplicateEventError,
    EventIdCollisionError,
    EventStoreCapacityError,
)
from log_parser_engine.models import (
    LogEvent,
    LogSeverity,
    LogSourceType,
)
from log_parser_engine.storage import InMemoryEventStore
from log_parser_engine.storage.options import (
    BatchWriteOptions,
    EventStoreOptions,
    EventWriteOptions,
)


@pytest.fixture
def make_log_event():
    """Factory fixture to create log events."""

    def _make(
        message: str,
        timestamp: datetime | None = None,
        severity: LogSeverity = LogSeverity.INFO,
        tags: list[str] | None = None,
        attributes: dict | None = None,
    ) -> LogEvent:
        return LogEvent(
            timestamp=timestamp or datetime.now(timezone.utc),
            source_type=LogSourceType.FILE,
            message=message,
            raw_message=message,
            severity=severity,
            tags=tags or [],
            attributes=attributes or {},
        )

    return _make


@pytest.fixture
def store() -> InMemoryEventStore:
    """A default, empty event store."""
    return InMemoryEventStore()


def test_add_single_event(store: InMemoryEventStore, make_log_event):
    """Tests adding a single event and confirms it's stored correctly."""
    event = make_log_event("message 1")
    result = store.add(event)

    assert result.status == "inserted"
    assert store.count() == 1
    stored = store.get(result.stored_event.id)
    assert stored is not None
    assert stored.event == event
    assert stored.sequence == 1


def test_add_many_events(store: InMemoryEventStore, make_log_event):
    """Tests adding a batch of events."""
    events = [make_log_event(f"message {i}") for i in range(5)]
    result = store.add_many(events)

    assert result.was_successful
    assert result.inserted_count == 5
    assert store.count() == 5
    # Check sequences
    assert result.inserted[0].sequence == 1
    assert result.inserted[4].sequence == 5


def test_duplicate_policy_ignore(make_log_event):
    """Tests the 'ignore' duplicate policy."""
    store = InMemoryEventStore(EventStoreOptions(duplicate_policy="ignore"))
    event = make_log_event("same message")

    result1 = store.add(event)
    assert result1.status == "inserted"
    assert store.count() == 1

    result2 = store.add(event)
    assert result2.status == "ignored_duplicate"
    assert store.count() == 1
    assert result1.stored_event.id == result2.stored_event.id


def test_duplicate_policy_reject(make_log_event):
    """Tests the 'reject' duplicate policy."""
    store = InMemoryEventStore(EventStoreOptions(duplicate_policy="reject"))
    event = make_log_event("same message")

    store.add(event)
    with pytest.raises(DuplicateEventError):
        store.add(event)
    assert store.count() == 1


def test_duplicate_policy_replace(make_log_event):
    """Tests the 'replace' duplicate policy."""
    store = InMemoryEventStore(
        EventStoreOptions(
            duplicate_policy="replace",
            identity_mode="content_hash",
        )
    )
    event1 = make_log_event("message")

    res1 = store.add(event1)
    assert res1.status == "inserted"
    assert store.count() == 1

    time.sleep(0.01)  # Ensure inserted_at is observably different.
    res2 = store.add(
        event1,
        options=EventWriteOptions(metadata={"revision": 2}),
    )
    assert res2.status == "replaced"
    assert store.count() == 1

    stored = store.get(res1.stored_event.id)
    assert stored is not None
    assert stored.id == res1.stored_event.id
    assert stored.sequence == res1.stored_event.sequence
    assert stored.event == event1
    assert stored.metadata == {"revision": 2}
    assert stored.inserted_at > res1.stored_event.inserted_at


def test_id_collision_error(store: InMemoryEventStore):
    """Tests that an ID collision raises an error."""
    event1 = LogEvent(
        event_id=uuid4(),
        timestamp=datetime.now(timezone.utc),
        source_type=LogSourceType.FILE,
        message="msg1",
        raw_message="msg1",
    )
    event2 = LogEvent(
        event_id=event1.event_id,
        timestamp=datetime.now(timezone.utc),
        source_type=LogSourceType.FILE,
        message="msg2",
        raw_message="msg2",
    )

    store.add(
        event1,
        options=EventWriteOptions(event_id=str(event1.event_id)),
    )
    with pytest.raises(EventIdCollisionError):
        store.add(
            event2,
            options=EventWriteOptions(event_id=str(event2.event_id)),
        )


def test_clear_store(store: InMemoryEventStore, make_log_event):
    """Tests clearing the store."""
    store.add_many([make_log_event(f"m{i}") for i in range(10)])
    assert store.count() == 10

    cleared_count = store.clear()
    assert cleared_count == 10
    assert store.count() == 0

    # Add again to ensure sequence numbers don't reset
    res = store.add(make_log_event("new"))
    assert res.stored_event.sequence > 10


def test_delete_event(store: InMemoryEventStore, make_log_event):
    """Tests deleting an event."""
    res = store.add(make_log_event("to_delete"))
    assert store.count() == 1

    was_deleted = store.delete(res.stored_event.id)
    assert was_deleted
    assert store.count() == 0
    assert store.get(res.stored_event.id) is None

    was_deleted_again = store.delete(res.stored_event.id)
    assert not was_deleted_again


def test_max_events_eviction(make_log_event):
    """Tests eviction when max_events is reached."""
    store = InMemoryEventStore(
        EventStoreOptions(
            max_events=5,
            eviction_policy="oldest_inserted",
        )
    )

    # Fill the store
    first_event_res = store.add(make_log_event("msg 0"))
    for i in range(1, 5):
        store.add(make_log_event(f"msg {i}"))

    assert store.count() == 5

    # Add one more to trigger eviction
    res = store.add(make_log_event("new event"))
    assert res.status == "inserted"
    assert len(res.evicted_event_ids) == 1
    assert res.evicted_event_ids[0] == first_event_res.stored_event.id
    assert store.count() == 5
    assert store.get(first_event_res.stored_event.id) is None


def test_retention_policy(make_log_event):
    """Tests the time-based retention policy."""
    store = InMemoryEventStore(
        EventStoreOptions(
            retention_seconds=60,
            retention_basis="event_timestamp",
        )
    )

    now = datetime.now(timezone.utc)
    store.add(make_log_event("recent", timestamp=now - timedelta(seconds=30)))
    store.add(make_log_event("old", timestamp=now - timedelta(seconds=90)))
    assert store.count() == 2

    # Add a new event, which should trigger retention check
    store.add(make_log_event("new"))
    
    # The old event should have been removed
    assert store.count() == 2
    results = store.query()
    assert len(results.events) == 2
    assert "old" not in [e.event.message for e in results.events]


def test_reject_new_policy(make_log_event):
    """Tests the reject_new eviction policy."""
    store = InMemoryEventStore(
        EventStoreOptions(max_events=1, eviction_policy="reject_new")
    )
    store.add(make_log_event("first"))
    assert store.count() == 1

    with pytest.raises(EventStoreCapacityError):
        store.add(make_log_event("second"))

    assert store.count() == 1


def test_ignored_duplicate_does_not_evict_at_capacity(make_log_event):
    """An ignored duplicate must be resolved before capacity eviction."""

    store = InMemoryEventStore(EventStoreOptions(max_events=1))
    event = make_log_event("same")
    first = store.add(event)

    duplicate = store.add(event)

    assert duplicate.status == "ignored_duplicate"
    assert duplicate.evicted_event_ids == ()
    assert store.count() == 1
    assert store.get(first.stored_event.id) == first.stored_event


def test_atomic_batch_rolls_back_on_duplicate_rejection(make_log_event):
    """An atomic batch must not retain writes before a later failure."""

    store = InMemoryEventStore(
        EventStoreOptions(duplicate_policy="reject")
    )
    duplicate = make_log_event("duplicate")
    first = make_log_event("first")

    result = store.add_many(
        (first, duplicate, duplicate),
        batch_options=BatchWriteOptions(atomic=True),
    )

    assert not result.was_successful
    assert result.errors == ("DuplicateEventError",)
    assert result.inserted == ()
    assert store.count() == 0
    assert store.statistics().write_count == 0

    next_result = store.add(make_log_event("after rollback"))
    assert next_result.stored_event.sequence == 1


def test_non_atomic_batch_reports_partial_success(make_log_event):
    """A non-atomic batch preserves earlier writes and reports safe errors."""

    store = InMemoryEventStore(
        EventStoreOptions(duplicate_policy="reject")
    )
    duplicate = make_log_event("duplicate")

    result = store.add_many(
        (make_log_event("first"), duplicate, duplicate),
        batch_options=BatchWriteOptions(
            atomic=False,
            stop_on_error=False,
        ),
    )

    assert result.inserted_count == 2
    assert result.errors == ("DuplicateEventError",)
    assert result.was_partial_success
    assert store.count() == 2


def test_atomic_capacity_failure_restores_evictions_and_sequence(
    make_log_event,
):
    """A failed atomic batch restores capacity evictions and sequence state."""

    store = InMemoryEventStore(
        EventStoreOptions(
            max_events=2,
            eviction_policy="reject_new",
        )
    )
    existing = store.add(make_log_event("existing"))

    result = store.add_many(
        (make_log_event("one"), make_log_event("two")),
        batch_options=BatchWriteOptions(atomic=True),
    )

    assert result.errors == ("EventStoreCapacityError",)
    assert store.count() == 1
    assert store.get(existing.stored_event.id) == existing.stored_event

    next_result = store.add(make_log_event("after rollback"))
    assert next_result.stored_event.sequence == 2
