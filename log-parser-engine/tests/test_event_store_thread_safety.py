
import threading
import time
from datetime import datetime, timezone

import pytest

from log_parser_engine.models import EventQuery, LogEvent, LogSourceType
from log_parser_engine.storage import InMemoryEventStore
from log_parser_engine.storage.options import EventStoreOptions


def test_concurrent_adds() -> None:
    """Tests that concurrent adds do not corrupt the store's state."""
    store = InMemoryEventStore(EventStoreOptions(max_events=1000))
    num_threads = 10
    events_per_thread = 100
    
    def worker(thread_id: int) -> None:
        for i in range(events_per_thread):
            message = f"event from thread {thread_id}-{i}"
            event = LogEvent(
                timestamp=datetime.now(timezone.utc),
                source_type=LogSourceType.FILE,
                message=message,
                raw_message=message,
            )
            store.add(event)

    threads = []
    for i in range(num_threads):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert store.count() == num_threads * events_per_thread
    stats = store.statistics()
    assert stats.event_count == num_threads * events_per_thread
    assert stats.write_count == num_threads * events_per_thread


def test_concurrent_add_and_query() -> None:
    """Tests that queries are consistent during concurrent writes."""
    store = InMemoryEventStore(EventStoreOptions(max_events=2000))
    stop_event = threading.Event()

    def writer() -> None:
        i = 0
        while not stop_event.is_set():
            message = f"event-{i}"
            event = LogEvent(
                timestamp=datetime.now(timezone.utc),
                source_type=LogSourceType.FILE,
                message=message,
                raw_message=message,
            )
            store.add(event)
            i += 1
            time.sleep(0.001)

    writer_thread = threading.Thread(target=writer)
    writer_thread.start()

    time.sleep(0.1)  # Let the writer add some events.

    # Perform some queries while the writer is active
    for _ in range(5):
        try:
            result = store.query(EventQuery(limit=500))
            # Main check is that this doesn't crash due to "dictionary changed size"
            assert result.page.returned <= 500
            # Due to snapshot consistency, total should be consistent within one result
            if result.page.total is not None:
                assert result.page.returned <= result.page.total
        except Exception as exc:
            pytest.fail(f"Query failed during concurrent writes: {exc}")
        time.sleep(0.01)

    stop_event.set()
    writer_thread.join()

    # Final check
    assert store.count() > 0


def test_concurrent_add_and_delete() -> None:
    """Tests concurrent additions and deletions."""
    store = InMemoryEventStore(EventStoreOptions(max_events=1000))
    initial_events = 100
    
    # Pre-populate the store
    ids_to_delete = []
    for i in range(initial_events):
        message = f"event-{i}"
        res = store.add(
            LogEvent(
                timestamp=datetime.now(timezone.utc),
                source_type=LogSourceType.FILE,
                message=message,
                raw_message=message,
            )
        )
        if i % 2 == 0:
            ids_to_delete.append(res.stored_event.id)

    def writer() -> None:
        for i in range(50):
            message = f"new-event-{i}"
            store.add(
                LogEvent(
                    timestamp=datetime.now(timezone.utc),
                    source_type=LogSourceType.FILE,
                    message=message,
                    raw_message=message,
                )
            )

    def deleter() -> None:
        for event_id in ids_to_delete:
            store.delete(event_id)

    w_thread = threading.Thread(target=writer)
    d_thread = threading.Thread(target=deleter)

    w_thread.start()
    d_thread.start()

    w_thread.join()
    d_thread.join()

    expected_count = initial_events - len(ids_to_delete) + 50
    assert store.count() == expected_count

    # Check that deleted events are gone
    for event_id in ids_to_delete:
        assert store.get(event_id) is None
