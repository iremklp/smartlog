
from __future__ import annotations

import bisect
import threading
from collections import OrderedDict, defaultdict
from datetime import datetime, timezone
from typing import Any, Iterable

from log_parser_engine.exceptions import (
    DuplicateEventError,
    EventIdCollisionError,
    EventStoreCapacityError,
    EventStoreConfigurationError,
    EventTooLargeForStoreError,
)
from log_parser_engine.models import (
    BatchWriteResult,
    EventQuery,
    EventQueryResult,
    EventStoreStatistics,
    EventWriteResult,
    LogEvent,
    StoredEvent,
)

from .base import EventStore
from .query_engine import InMemoryEventQueryEngine
from .helpers import estimate_event_size_bytes, get_canonical_json_bytes
from .identity import compute_event_content_hash, generate_event_id
from .options import BatchWriteOptions, EventStoreOptions, EventWriteOptions
from .retention import determine_expired_event_ids, get_eviction_candidates


class InMemoryEventStore(EventStore):
    """
    An in-memory, thread-safe implementation of the EventStore protocol.
    """

    def __init__(self, options: EventStoreOptions | None = None):
        self._options = options or EventStoreOptions()
        if not isinstance(self._options, EventStoreOptions):
            raise EventStoreConfigurationError("options must be an instance of EventStoreOptions")

        # Core data structures
        self._events_by_id: dict[str, StoredEvent] = {}
        self._sequence_ids: OrderedDict[str, None] = OrderedDict()
        self._timestamp_index: list[tuple[datetime, int, str]] = []

        # Indexes
        self._hash_to_ids: defaultdict[str, set[str]] = defaultdict(set)
        self._indexes: defaultdict[str, defaultdict[Any, set[str]]] = defaultdict(lambda: defaultdict(set))

        # Statistics and state
        self._total_estimated_bytes: int = 0
        self._next_sequence: int = 1
        self._lock = threading.RLock()

        # Counters
        self._created_at = datetime.now(timezone.utc)
        self._write_count = 0
        self._query_count = 0
        self._delete_count = 0
        self._clear_count = 0
        self._duplicate_ignored_count = 0
        self._replaced_count = 0
        self._evicted_count = 0
        self._retention_removed_count = 0
        self._last_write_at: datetime | None = None
        self._last_query_at: datetime | None = None
        self._last_retention_at: datetime | None = None

    def add(
        self,
        event: LogEvent,
        *,
        options: EventWriteOptions | None = None,
    ) -> EventWriteResult:
        batch_result = self.add_many([event], options=options)
        
        if batch_result.errors:
             # Errors in a single-add batch should raise an exception
            raise ValueError(f"Failed to add event: {batch_result.errors[0]}")

        if batch_result.inserted:
            return EventWriteResult(status="inserted", stored_event=batch_result.inserted[0], evicted_event_ids=batch_result.evicted_event_ids)
        if batch_result.replaced:
            return EventWriteResult(status="replaced", stored_event=batch_result.replaced[0], evicted_event_ids=batch_result.evicted_event_ids)
        
        # This must be an ignored duplicate
        ignored_id = batch_result.ignored_event_ids[0]
        existing_event = self.get(ignored_id)
        if existing_event:
            return EventWriteResult(status="ignored_duplicate", stored_event=existing_event, evicted_event_ids=batch_result.evicted_event_ids)
        
        raise RuntimeError("Internal error in add method: unexpected batch result")

    def add_many(
        self,
        events: Iterable[LogEvent],
        *,
        options: EventWriteOptions | None = None,
        batch_options: BatchWriteOptions | None = None,
    ) -> BatchWriteResult:
        write_opts = options or EventWriteOptions()
        batch_opts = batch_options or BatchWriteOptions()
        
        # Non-atomic implementation for now
        if batch_opts.atomic:
            # Full atomic implementation is complex and will be added later.
            pass

        inserted_events, ignored_ids, replaced_events, errors = [], [], [], []
        evicted_ids = set()

        with self._lock:
            if write_opts.apply_retention_before_write and self._options.retention_seconds:
                expired_ids = self._apply_retention_unsafe()
                evicted_ids.update(expired_ids)

            for event in events:
                try:
                    evicted_in_loop = self._add_one_unsafe(event, write_opts)
                    evicted_ids.update(evicted_in_loop.evicted_event_ids)
                    
                    if evicted_in_loop.status == "inserted":
                        inserted_events.append(evicted_in_loop.stored_event)
                    elif evicted_in_loop.status == "replaced":
                        replaced_events.append(evicted_in_loop.stored_event)
                    else: # ignored_duplicate
                        ignored_ids.append(evicted_in_loop.stored_event.id)

                except Exception as e:
                    errors.append(str(e))
                    if batch_opts.stop_on_error:
                        break
        
        self._last_write_at = datetime.now(timezone.utc)
        self._write_count += len(inserted_events) + len(replaced_events)
        
        return BatchWriteResult(
            inserted=tuple(inserted_events),
            ignored_event_ids=tuple(ignored_ids),
            replaced=tuple(replaced_events),
            evicted_event_ids=tuple(sorted(list(evicted_ids))),
            errors=tuple(errors),
            atomic=batch_opts.atomic,
        )

    def _add_one_unsafe(self, event: LogEvent, options: EventWriteOptions) -> EventWriteResult:
        """Adds a single event. Must be called within a lock."""
        canonical_bytes = get_canonical_json_bytes(event)
        estimated_size = estimate_event_size_bytes(canonical_bytes)

        # Eviction plan
        evicted_this_turn: list[str] = []
        if self._options.eviction_policy == "reject_new":
            if len(self._events_by_id) >= self._options.max_events:
                raise EventStoreCapacityError(f"Store at max events capacity ({self._options.max_events})")
            if self._options.max_estimated_memory_bytes and (self._total_estimated_bytes + estimated_size) > self._options.max_estimated_memory_bytes:
                raise EventStoreCapacityError(f"Store at max memory capacity")
        else:
            # Regular eviction
            num_to_evict = 0
            # Check event count limit
            if len(self._events_by_id) >= self._options.max_events:
                num_to_evict = len(self._events_by_id) - self._options.max_events + 1
            
            # Check memory limit
            if self._options.max_estimated_memory_bytes:
                mem_overflow = (self._total_estimated_bytes + estimated_size) - self._options.max_estimated_memory_bytes
                if mem_overflow > 0:
                    # Find how many oldest events we need to evict to free enough space
                    space_needed = mem_overflow
                    space_freed = 0
                    eviction_candidates = self._get_eviction_candidates(len(self._events_by_id))
                    
                    evicted_count_for_mem = 0
                    for candidate_id in eviction_candidates:
                        if space_freed >= space_needed:
                            break
                        space_freed += self._events_by_id[candidate_id].estimated_size_bytes
                        evicted_count_for_mem += 1
                    
                    num_to_evict = max(num_to_evict, evicted_count_for_mem)

            if num_to_evict > 0:
                candidates = self._get_eviction_candidates(num_to_evict)
                for event_id in candidates:
                    self._delete_unsafe(event_id)
                    evicted_this_turn.append(event_id)
                self._evicted_count += len(evicted_this_turn)

        event_id, content_hash = generate_event_id(event, mode=self._options.identity_mode, existing_id=str(event.event_id))
        duplicate_policy = options.duplicate_policy or self._options.duplicate_policy

        if event_id in self._events_by_id and self._events_by_id[event_id].content_hash != content_hash:
            raise EventIdCollisionError(f"Event ID '{event_id}' collision detected.")

        if content_hash in self._hash_to_ids:
            if duplicate_policy == "reject":
                raise DuplicateEventError(f"Duplicate event with hash {content_hash} rejected.")
            elif duplicate_policy == "ignore":
                self._duplicate_ignored_count += 1
                existing_id = next(iter(self._hash_to_ids[content_hash]))
                return EventWriteResult(status="ignored_duplicate", stored_event=self._events_by_id[existing_id], evicted_event_ids=tuple(evicted_this_turn))

        stored_event = StoredEvent(
            id=event_id, event=event, inserted_at=datetime.now(timezone.utc),
            sequence=self._next_sequence, content_hash=content_hash, estimated_size_bytes=estimated_size,
            source_batch_id=options.source_batch_id, metadata=options.metadata
        )

        status: Literal["inserted", "replaced"] = "inserted"
        if event_id in self._events_by_id:
            self._replace_event_unsafe(self._events_by_id[event_id], stored_event)
            self._replaced_count += 1
            status = "replaced"
        else:
            self._insert_event_unsafe(stored_event)
        
        self._next_sequence += 1
        return EventWriteResult(status=status, stored_event=stored_event, evicted_event_ids=tuple(evicted_this_turn))

    def _insert_event_unsafe(self, event: StoredEvent):
        """Inserts a new event. Must be called within a lock."""
        self._events_by_id[event.id] = event
        self._sequence_ids[event.id] = None
        bisect.insort(self._timestamp_index, (event.timestamp, event.sequence, event.id))
        self._hash_to_ids[event.content_hash].add(event.id)
        self._total_estimated_bytes += event.estimated_size_bytes
        self._update_indexes_for_event(event, "add")

    def _replace_event_unsafe(self, old_event: StoredEvent, new_event: StoredEvent):
        """Replaces an event. Must be called within a lock."""
        new_event = new_event.model_copy(update={"sequence": old_event.sequence})
        self._events_by_id[new_event.id] = new_event
        
        self._update_indexes_for_event(old_event, "remove")
        self._timestamp_index.remove((old_event.timestamp, old_event.sequence, old_event.id))
        self._hash_to_ids[old_event.content_hash].discard(old_event.id)
        if not self._hash_to_ids[old_event.content_hash]:
            del self._hash_to_ids[old_event.content_hash]
        
        bisect.insort(self._timestamp_index, (new_event.timestamp, new_event.sequence, new_event.id))
        self._hash_to_ids[new_event.content_hash].add(new_event.id)
        self._update_indexes_for_event(new_event, "add")

        self._total_estimated_bytes += (new_event.estimated_size_bytes - old_event.estimated_size_bytes)

    def _delete_unsafe(self, event_id: str) -> bool:
        """Deletes an event. Must be called within a lock."""
        event_to_delete = self._events_by_id.pop(event_id, None)
        if not event_to_delete:
            return False

        del self._sequence_ids[event_id]
        self._timestamp_index.remove((event_to_delete.timestamp, event_to_delete.sequence, event_to_delete.id))
        
        self._hash_to_ids[event_to_delete.content_hash].discard(event_id)
        if not self._hash_to_ids[event_to_delete.content_hash]:
            del self._hash_to_ids[event_to_delete.content_hash]

        self._total_estimated_bytes -= event_to_delete.estimated_size_bytes
        self._update_indexes_for_event(event_to_delete, "remove")
        return True

    def delete(self, event_id: str) -> bool:
        with self._lock:
            was_deleted = self._delete_unsafe(event_id)
            if was_deleted:
                self._delete_count += 1
        return was_deleted

    def get(self, event_id: str) -> StoredEvent | None:
        with self._lock:
            return self._events_by_id.get(event_id)

    def count(self) -> int:
        with self._lock:
            return len(self._events_by_id)

    def clear(self) -> int:
        with self._lock:
            removed_count = len(self._events_by_id)
            if removed_count == 0:
                return 0
            self.__init__(self._options) # Re-initialize to clear state
            self._clear_count += 1
        return removed_count

    def statistics(self) -> EventStoreStatistics:
        with self._lock:
            return EventStoreStatistics(
                event_count=len(self._events_by_id),
                estimated_memory_bytes=self._total_estimated_bytes,
                max_events=self._options.max_events,
                max_estimated_memory_bytes=self._options.max_estimated_memory_bytes,
                oldest_inserted_at=self._events_by_id[next(iter(self._sequence_ids))].inserted_at if self._sequence_ids else None,
                newest_inserted_at=self._events_by_id[next(reversed(self._sequence_ids))].inserted_at if self._sequence_ids else None,
                earliest_event_timestamp=self._timestamp_index[0][0] if self._timestamp_index else None,
                latest_event_timestamp=self._timestamp_index[-1][0] if self._timestamp_index else None,
                index_enabled=self._options.enable_indexes,
                indexed_field_count=len(self._options.indexed_fields),
                duplicate_ignored_count=self._duplicate_ignored_count,
                replaced_count=self._replaced_count,
                evicted_count=self._evicted_count,
                retention_removed_count=self._retention_removed_count,
                write_count=self._write_count,
                query_count=self._query_count,
                delete_count=self._delete_count,
                clear_count=self._clear_count,
                created_at=self._created_at,
                last_write_at=self._last_write_at,
                last_query_at=self._last_query_at,
                last_retention_at=self._last_retention_at,
            )

    def _update_indexes_for_event(self, event: StoredEvent, action: Literal["add", "remove"]):
        if not self._options.enable_indexes:
            return

        for field in self._options.indexed_fields:
            value = getattr(event.event, field, None)
            if value is None:
                continue

            if field == "tags" and isinstance(value, list):
                for tag in value:
                    if action == "add":
                        self._indexes[field][tag].add(event.id)
                    else:
                        self._indexes[field][tag].discard(event.id)
            elif isinstance(value, (str, int, float, bool)) or hasattr(value, "value"):
                key = value.value if hasattr(value, "value") else value
                if action == "add":
                    self._indexes[field][key].add(event.id)
                else:
                    self._indexes[field][key].discard(event.id)

    def _get_eviction_candidates(self, num_to_evict: int) -> tuple[str, ...]:
        return get_eviction_candidates(
            num_to_evict=num_to_evict,
            policy=self._options.eviction_policy,
            sequence_ids=list(self._sequence_ids.keys()),
            timestamp_index=self._timestamp_index,
        )
    
    def _apply_retention_unsafe(self) -> list[str]:
        """Applies retention policy. Must be called within a lock."""
        if not self._options.retention_seconds:
            return []
            
        now = datetime.now(timezone.utc)
        all_events = list(self._events_by_id.values())

        expired_ids = determine_expired_event_ids(
            events=all_events,
            now=now,
            retention_seconds=self._options.retention_seconds,
            basis=self._options.retention_basis
        )
        
        for event_id in expired_ids:
            self._delete_unsafe(event_id)
        
        if expired_ids:
            self._retention_removed_count += len(expired_ids)
            self._last_retention_at = now
        
        return list(expired_ids)

    def query(self, query: EventQuery | None = None) -> EventQueryResult:
        q = query or EventQuery()

        with self._lock:
            # Snapshot consistency: Copy references to data structures under a lock.
            # The query engine will operate on this immutable snapshot.
            snapshot_events = self._events_by_id.copy()
            snapshot_indexes = self._indexes.copy() # Shallow copy is enough
            snapshot_timestamp_index = list(self._timestamp_index)
            self._query_count += 1
            self._last_query_at = datetime.now(timezone.utc)

        # The lock is released here, so writes don't block the query.
        engine = InMemoryEventQueryEngine(
            options=self._options,
            query=q,
            events=snapshot_events,
            indexes=snapshot_indexes,
            timestamp_index=snapshot_timestamp_index,
        )
        return engine.execute()

