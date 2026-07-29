from __future__ import annotations

import bisect
import threading
from collections import OrderedDict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from log_parser_engine.exceptions import (
    BatchWriteError,
    DuplicateEventError,
    EventIdCollisionError,
    EventStoreCapacityError,
    EventStoreConfigurationError,
    EventStoreError,
    EventTooLargeForStoreError,
    InvalidEventError,
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
from .helpers import estimate_event_size_bytes, get_canonical_json_bytes
from .identity import compute_event_content_hash, generate_event_id
from .options import BatchWriteOptions, EventStoreOptions, EventWriteOptions
from .query_engine import InMemoryEventQueryEngine
from .retention import determine_expired_event_ids, get_eviction_candidates


@dataclass(slots=True)
class _StoreStateSnapshot:
    events_by_id: dict[str, StoredEvent]
    sequence_ids: OrderedDict[str, None]
    timestamp_index: list[tuple[datetime, int, str]]
    hash_to_ids: dict[str, set[str]]
    indexes: dict[str, dict[Any, set[str]]]
    total_estimated_bytes: int
    next_sequence: int
    write_count: int
    query_count: int
    delete_count: int
    clear_count: int
    duplicate_ignored_count: int
    replaced_count: int
    evicted_count: int
    retention_removed_count: int
    last_write_at: datetime | None
    last_query_at: datetime | None
    last_retention_at: datetime | None


class InMemoryEventStore(EventStore):
    """Thread-safe, bounded and process-local event store."""

    def __init__(self, options: EventStoreOptions | None = None) -> None:
        resolved_options = options if options is not None else EventStoreOptions()
        if not isinstance(resolved_options, EventStoreOptions):
            raise EventStoreConfigurationError(
                "options must be an EventStoreOptions instance"
            )
        self._options = resolved_options

        self._events_by_id: dict[str, StoredEvent] = {}
        self._sequence_ids: OrderedDict[str, None] = OrderedDict()
        self._timestamp_index: list[tuple[datetime, int, str]] = []
        self._hash_to_ids: dict[str, set[str]] = {}
        self._indexes: dict[str, dict[Any, set[str]]] = {}
        self._total_estimated_bytes = 0
        self._next_sequence = 1
        self._lock = threading.RLock()

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

    @property
    def options(self) -> EventStoreOptions:
        """Return the immutable store options."""

        return self._options

    def add(
        self,
        event: LogEvent,
        *,
        options: EventWriteOptions | None = None,
    ) -> EventWriteResult:
        """Add one event and preserve typed storage exceptions."""

        write_options = self._resolve_write_options(options)
        with self._lock:
            snapshot = self._snapshot_state_unsafe()
            retention_ids: tuple[str, ...] = ()
            try:
                if (
                    write_options.apply_retention_before_write
                    and self._options.retention_seconds is not None
                ):
                    retention_ids = self._apply_retention_unsafe()
                result = self._add_one_unsafe(event, write_options)
            except Exception:
                self._restore_state_unsafe(snapshot)
                raise

            if result.status in {"inserted", "replaced"}:
                self._write_count += 1
                self._last_write_at = datetime.now(timezone.utc)
            return result.model_copy(
                update={
                    "evicted_event_ids": self._merge_ids(
                        retention_ids,
                        result.evicted_event_ids,
                    )
                }
            )

    def add_many(
        self,
        events: Iterable[LogEvent],
        *,
        options: EventWriteOptions | None = None,
        batch_options: BatchWriteOptions | None = None,
    ) -> BatchWriteResult:
        """Add a bounded batch, optionally with all-or-nothing semantics."""

        write_options = self._resolve_write_options(options)
        resolved_batch_options = self._resolve_batch_options(batch_options)
        materialized = self._materialize_events(events, resolved_batch_options)
        if not materialized:
            return BatchWriteResult(atomic=resolved_batch_options.atomic)

        with self._lock:
            snapshot = (
                self._snapshot_state_unsafe()
                if resolved_batch_options.atomic
                else None
            )
            inserted: list[StoredEvent] = []
            replaced: list[StoredEvent] = []
            ignored_ids: list[str] = []
            evicted_ids: list[str] = []
            errors: list[str] = []

            if (
                write_options.apply_retention_before_write
                and self._options.retention_seconds is not None
            ):
                self._extend_unique(
                    evicted_ids,
                    self._apply_retention_unsafe(),
                )

            for event in materialized:
                try:
                    result = self._add_one_unsafe(event, write_options)
                except Exception as exc:  # noqa: BLE001
                    errors.append(self._safe_error_code(exc))
                    if resolved_batch_options.atomic:
                        if snapshot is None:
                            raise RuntimeError(
                                "atomic batch snapshot is unavailable"
                            )
                        self._restore_state_unsafe(snapshot)
                        return BatchWriteResult(
                            errors=tuple(errors),
                            atomic=True,
                        )
                    if resolved_batch_options.stop_on_error:
                        break
                    continue

                self._extend_unique(evicted_ids, result.evicted_event_ids)
                if result.status == "inserted":
                    inserted.append(result.stored_event)
                elif result.status == "replaced":
                    replaced.append(result.stored_event)
                else:
                    ignored_ids.append(result.stored_event.id)

            successful_writes = len(inserted) + len(replaced)
            if successful_writes:
                self._write_count += successful_writes
                self._last_write_at = datetime.now(timezone.utc)

            return BatchWriteResult(
                inserted=tuple(inserted),
                ignored_event_ids=tuple(ignored_ids),
                replaced=tuple(replaced),
                evicted_event_ids=tuple(evicted_ids),
                errors=tuple(errors),
                atomic=resolved_batch_options.atomic,
            )

    def get(self, event_id: str) -> StoredEvent | None:
        with self._lock:
            return self._events_by_id.get(event_id)

    def delete(self, event_id: str) -> bool:
        with self._lock:
            deleted = self._delete_unsafe(event_id)
            if deleted:
                self._delete_count += 1
            return deleted

    def count(self) -> int:
        with self._lock:
            return len(self._events_by_id)

    def clear(self) -> int:
        """Clear event data while preserving lifecycle counters and sequence."""

        with self._lock:
            removed_count = len(self._events_by_id)
            if removed_count == 0:
                return 0
            self._events_by_id.clear()
            self._sequence_ids.clear()
            self._timestamp_index.clear()
            self._hash_to_ids.clear()
            self._indexes.clear()
            self._total_estimated_bytes = 0
            self._clear_count += 1
            return removed_count

    def statistics(self) -> EventStoreStatistics:
        with self._lock:
            oldest_id = next(iter(self._sequence_ids), None)
            newest_id = next(reversed(self._sequence_ids), None)
            return EventStoreStatistics(
                event_count=len(self._events_by_id),
                estimated_memory_bytes=self._total_estimated_bytes,
                max_events=self._options.max_events,
                max_estimated_memory_bytes=(
                    self._options.max_estimated_memory_bytes
                ),
                oldest_inserted_at=(
                    self._events_by_id[oldest_id].inserted_at
                    if oldest_id is not None
                    else None
                ),
                newest_inserted_at=(
                    self._events_by_id[newest_id].inserted_at
                    if newest_id is not None
                    else None
                ),
                earliest_event_timestamp=(
                    self._timestamp_index[0][0]
                    if self._timestamp_index
                    else None
                ),
                latest_event_timestamp=(
                    self._timestamp_index[-1][0]
                    if self._timestamp_index
                    else None
                ),
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

    def query(self, query: EventQuery | None = None) -> EventQueryResult:
        resolved_query = query if query is not None else EventQuery()
        with self._lock:
            snapshot_events = dict(self._events_by_id)
            snapshot_indexes = {
                field: {
                    value: set(event_ids)
                    for value, event_ids in values.items()
                }
                for field, values in self._indexes.items()
            }
            snapshot_timestamp_index = list(self._timestamp_index)
            self._query_count += 1
            self._last_query_at = datetime.now(timezone.utc)

        engine = InMemoryEventQueryEngine(
            options=self._options,
            query=resolved_query,
            events=snapshot_events,
            indexes=snapshot_indexes,
            timestamp_index=snapshot_timestamp_index,
        )
        return engine.execute()

    def snapshot_events(self) -> tuple[StoredEvent, ...]:
        """Return a consistent sequence-ordered immutable-reference snapshot."""

        with self._lock:
            return tuple(
                sorted(
                    self._events_by_id.values(),
                    key=lambda item: item.sequence,
                )
            )

    def _add_one_unsafe(
        self,
        event: LogEvent,
        options: EventWriteOptions,
    ) -> EventWriteResult:
        if not isinstance(event, LogEvent):
            raise InvalidEventError("event must be a LogEvent")

        try:
            canonical_bytes = get_canonical_json_bytes(event)
            content_hash = compute_event_content_hash(event)
        except (TypeError, ValueError) as exc:
            raise InvalidEventError(
                "event contains non-serializable canonical data"
            ) from exc

        estimated_size = estimate_event_size_bytes(canonical_bytes)
        memory_limit = self._options.max_estimated_memory_bytes
        if memory_limit is not None and estimated_size > memory_limit:
            raise EventTooLargeForStoreError(
                "event exceeds the configured store memory limit"
            )

        existing_id = options.event_id or str(event.event_id)
        event_id, generated_hash = generate_event_id(
            event,
            mode=self._options.identity_mode,
            existing_id=existing_id,
        )
        if generated_hash != content_hash:
            raise RuntimeError("event hash generation is inconsistent")

        existing_by_id = self._events_by_id.get(event_id)
        if (
            existing_by_id is not None
            and existing_by_id.content_hash != content_hash
        ):
            raise EventIdCollisionError("event ID collision detected")

        duplicate_policy = (
            options.duplicate_policy or self._options.duplicate_policy
        )
        duplicate_target = self._find_duplicate_target_unsafe(
            content_hash=content_hash,
            existing_by_id=existing_by_id,
            deduplicate=options.deduplicate is not False,
        )
        if duplicate_target is not None:
            if duplicate_policy == "reject":
                raise DuplicateEventError("duplicate event rejected")
            if duplicate_policy == "ignore":
                self._duplicate_ignored_count += 1
                return EventWriteResult(
                    status="ignored_duplicate",
                    stored_event=duplicate_target,
                )
            return self._replace_duplicate_unsafe(
                target=duplicate_target,
                event=event,
                content_hash=content_hash,
                estimated_size=estimated_size,
                options=options,
            )

        evicted_ids = self._plan_capacity_unsafe(
            new_size=estimated_size,
            replacing_id=None,
        )
        self._execute_evictions_unsafe(evicted_ids)
        stored_event = StoredEvent(
            id=event_id,
            event=event,
            inserted_at=datetime.now(timezone.utc),
            sequence=self._next_sequence,
            content_hash=content_hash,
            estimated_size_bytes=estimated_size,
            source_batch_id=options.source_batch_id,
            metadata=options.metadata,
        )
        self._insert_event_unsafe(stored_event)
        self._next_sequence += 1
        return EventWriteResult(
            status="inserted",
            stored_event=stored_event,
            evicted_event_ids=evicted_ids,
        )

    def _replace_duplicate_unsafe(
        self,
        *,
        target: StoredEvent,
        event: LogEvent,
        content_hash: str,
        estimated_size: int,
        options: EventWriteOptions,
    ) -> EventWriteResult:
        evicted_ids = self._plan_capacity_unsafe(
            new_size=estimated_size,
            replacing_id=target.id,
        )
        self._execute_evictions_unsafe(evicted_ids)
        replacement = StoredEvent(
            id=target.id,
            event=event,
            inserted_at=datetime.now(timezone.utc),
            sequence=target.sequence,
            content_hash=content_hash,
            estimated_size_bytes=estimated_size,
            source_batch_id=options.source_batch_id,
            metadata=options.metadata,
        )
        self._replace_event_unsafe(target, replacement)
        self._replaced_count += 1
        return EventWriteResult(
            status="replaced",
            stored_event=replacement,
            evicted_event_ids=evicted_ids,
        )

    def _find_duplicate_target_unsafe(
        self,
        *,
        content_hash: str,
        existing_by_id: StoredEvent | None,
        deduplicate: bool,
    ) -> StoredEvent | None:
        if existing_by_id is not None:
            return existing_by_id
        if not deduplicate:
            return None
        candidate_ids = self._hash_to_ids.get(content_hash, set())
        if not candidate_ids:
            return None
        return min(
            (self._events_by_id[event_id] for event_id in candidate_ids),
            key=lambda stored: stored.sequence,
        )

    def _plan_capacity_unsafe(
        self,
        *,
        new_size: int,
        replacing_id: str | None,
    ) -> tuple[str, ...]:
        replaced = (
            self._events_by_id.get(replacing_id)
            if replacing_id is not None
            else None
        )
        projected_count = len(self._events_by_id) + (0 if replaced else 1)
        projected_bytes = (
            self._total_estimated_bytes
            - (replaced.estimated_size_bytes if replaced else 0)
            + new_size
        )
        if self._fits_capacity(projected_count, projected_bytes):
            return ()
        if self._options.eviction_policy == "reject_new":
            raise EventStoreCapacityError("event store capacity exceeded")

        candidates = self._get_eviction_candidates(len(self._events_by_id))
        planned: list[str] = []
        for candidate_id in candidates:
            if candidate_id == replacing_id:
                continue
            candidate = self._events_by_id[candidate_id]
            planned.append(candidate_id)
            projected_count -= 1
            projected_bytes -= candidate.estimated_size_bytes
            if self._fits_capacity(projected_count, projected_bytes):
                return tuple(planned)
        raise EventStoreCapacityError("event store capacity cannot be satisfied")

    def _fits_capacity(self, event_count: int, estimated_bytes: int) -> bool:
        if event_count > self._options.max_events:
            return False
        memory_limit = self._options.max_estimated_memory_bytes
        return memory_limit is None or estimated_bytes <= memory_limit

    def _execute_evictions_unsafe(self, event_ids: tuple[str, ...]) -> None:
        for event_id in event_ids:
            if self._delete_unsafe(event_id):
                self._evicted_count += 1

    def _insert_event_unsafe(self, event: StoredEvent) -> None:
        self._events_by_id[event.id] = event
        self._sequence_ids[event.id] = None
        bisect.insort(
            self._timestamp_index,
            (event.timestamp, event.sequence, event.id),
        )
        self._hash_to_ids.setdefault(event.content_hash, set()).add(event.id)
        self._total_estimated_bytes += event.estimated_size_bytes
        self._update_indexes_for_event(event, "add")

    def _replace_event_unsafe(
        self,
        old_event: StoredEvent,
        new_event: StoredEvent,
    ) -> None:
        self._update_indexes_for_event(old_event, "remove")
        self._timestamp_index.remove(
            (old_event.timestamp, old_event.sequence, old_event.id)
        )
        old_hash_ids = self._hash_to_ids[old_event.content_hash]
        old_hash_ids.discard(old_event.id)
        if not old_hash_ids:
            del self._hash_to_ids[old_event.content_hash]

        self._events_by_id[new_event.id] = new_event
        bisect.insort(
            self._timestamp_index,
            (new_event.timestamp, new_event.sequence, new_event.id),
        )
        self._hash_to_ids.setdefault(new_event.content_hash, set()).add(
            new_event.id
        )
        self._update_indexes_for_event(new_event, "add")
        self._total_estimated_bytes += (
            new_event.estimated_size_bytes - old_event.estimated_size_bytes
        )

    def _delete_unsafe(self, event_id: str) -> bool:
        event = self._events_by_id.pop(event_id, None)
        if event is None:
            return False
        self._sequence_ids.pop(event_id, None)
        self._timestamp_index.remove(
            (event.timestamp, event.sequence, event.id)
        )
        hash_ids = self._hash_to_ids[event.content_hash]
        hash_ids.discard(event_id)
        if not hash_ids:
            del self._hash_to_ids[event.content_hash]
        self._total_estimated_bytes -= event.estimated_size_bytes
        self._update_indexes_for_event(event, "remove")
        return True

    def _update_indexes_for_event(
        self,
        event: StoredEvent,
        action: Literal["add", "remove"],
    ) -> None:
        if not self._options.enable_indexes:
            return
        for field in self._options.indexed_fields:
            for value in self._index_values(event, field):
                key = value.value if hasattr(value, "value") else value
                self._update_index_value(field, key, event.id, action)

    @staticmethod
    def _index_values(
        event: StoredEvent,
        field: str,
    ) -> tuple[object, ...]:
        if field == "parser_name":
            parser_name = event.event.attributes.get("parser_name")
            return (parser_name,) if isinstance(parser_name, str) else ()
        if field == "tags":
            return tuple(event.event.tags)

        value = getattr(event.event, field, None)
        if isinstance(value, (str, int, float, bool)) or hasattr(
            value,
            "value",
        ):
            return (value,)
        return ()

    def _update_index_value(
        self,
        field: str,
        value: Any,
        event_id: str,
        action: Literal["add", "remove"],
    ) -> None:
        if action == "add":
            self._indexes.setdefault(field, {}).setdefault(value, set()).add(
                event_id
            )
            return
        field_index = self._indexes.get(field)
        if field_index is None:
            return
        ids = field_index.get(value)
        if ids is None:
            return
        ids.discard(event_id)
        if not ids:
            del field_index[value]
        if not field_index:
            del self._indexes[field]

    def _get_eviction_candidates(
        self,
        num_to_evict: int,
    ) -> tuple[str, ...]:
        return get_eviction_candidates(
            num_to_evict=num_to_evict,
            policy=self._options.eviction_policy,
            sequence_ids=list(self._sequence_ids),
            timestamp_index=self._timestamp_index,
        )

    def _apply_retention_unsafe(self) -> tuple[str, ...]:
        retention_seconds = self._options.retention_seconds
        if retention_seconds is None:
            return ()
        now = datetime.now(timezone.utc)
        expired_ids = determine_expired_event_ids(
            events=self._events_by_id.values(),
            now=now,
            retention_seconds=retention_seconds,
            basis=self._options.retention_basis,
        )
        removed: list[str] = []
        for event_id in expired_ids:
            if self._delete_unsafe(event_id):
                removed.append(event_id)
        if removed:
            self._retention_removed_count += len(removed)
            self._last_retention_at = now
        return tuple(removed)

    def _materialize_events(
        self,
        events: Iterable[LogEvent],
        options: BatchWriteOptions,
    ) -> tuple[LogEvent, ...]:
        if isinstance(events, (str, bytes)):
            raise BatchWriteError("events must be an iterable of LogEvent values")
        configured_limit = self._options.max_batch_events
        requested_limit = options.max_events or configured_limit
        if requested_limit > configured_limit:
            raise BatchWriteError(
                "batch max_events cannot exceed the configured store limit"
            )

        materialized: list[LogEvent] = []
        try:
            for event in events:
                if len(materialized) >= requested_limit:
                    raise BatchWriteError("batch event limit exceeded")
                if not isinstance(event, LogEvent):
                    raise InvalidEventError(
                        "batch contains a value that is not a LogEvent"
                    )
                materialized.append(event)
        except EventStoreError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise BatchWriteError("event iterable failed") from exc
        return tuple(materialized)

    def _resolve_write_options(
        self,
        options: EventWriteOptions | None,
    ) -> EventWriteOptions:
        if options is None:
            return EventWriteOptions()
        if not isinstance(options, EventWriteOptions):
            raise TypeError("options must be EventWriteOptions")
        return options

    def _resolve_batch_options(
        self,
        options: BatchWriteOptions | None,
    ) -> BatchWriteOptions:
        if options is None:
            return BatchWriteOptions()
        if not isinstance(options, BatchWriteOptions):
            raise TypeError("batch_options must be BatchWriteOptions")
        return options

    def _snapshot_state_unsafe(self) -> _StoreStateSnapshot:
        return _StoreStateSnapshot(
            events_by_id=dict(self._events_by_id),
            sequence_ids=OrderedDict(self._sequence_ids),
            timestamp_index=list(self._timestamp_index),
            hash_to_ids={
                content_hash: set(event_ids)
                for content_hash, event_ids in self._hash_to_ids.items()
            },
            indexes={
                field: {
                    value: set(event_ids)
                    for value, event_ids in values.items()
                }
                for field, values in self._indexes.items()
            },
            total_estimated_bytes=self._total_estimated_bytes,
            next_sequence=self._next_sequence,
            write_count=self._write_count,
            query_count=self._query_count,
            delete_count=self._delete_count,
            clear_count=self._clear_count,
            duplicate_ignored_count=self._duplicate_ignored_count,
            replaced_count=self._replaced_count,
            evicted_count=self._evicted_count,
            retention_removed_count=self._retention_removed_count,
            last_write_at=self._last_write_at,
            last_query_at=self._last_query_at,
            last_retention_at=self._last_retention_at,
        )

    def _restore_state_unsafe(self, snapshot: _StoreStateSnapshot) -> None:
        self._events_by_id = snapshot.events_by_id
        self._sequence_ids = snapshot.sequence_ids
        self._timestamp_index = snapshot.timestamp_index
        self._hash_to_ids = snapshot.hash_to_ids
        self._indexes = snapshot.indexes
        self._total_estimated_bytes = snapshot.total_estimated_bytes
        self._next_sequence = snapshot.next_sequence
        self._write_count = snapshot.write_count
        self._query_count = snapshot.query_count
        self._delete_count = snapshot.delete_count
        self._clear_count = snapshot.clear_count
        self._duplicate_ignored_count = snapshot.duplicate_ignored_count
        self._replaced_count = snapshot.replaced_count
        self._evicted_count = snapshot.evicted_count
        self._retention_removed_count = snapshot.retention_removed_count
        self._last_write_at = snapshot.last_write_at
        self._last_query_at = snapshot.last_query_at
        self._last_retention_at = snapshot.last_retention_at

    @staticmethod
    def _safe_error_code(exc: Exception) -> str:
        return exc.__class__.__name__

    @staticmethod
    def _merge_ids(
        first: Iterable[str],
        second: Iterable[str],
    ) -> tuple[str, ...]:
        merged: list[str] = []
        InMemoryEventStore._extend_unique(merged, first)
        InMemoryEventStore._extend_unique(merged, second)
        return tuple(merged)

    @staticmethod
    def _extend_unique(target: list[str], values: Iterable[str]) -> None:
        existing = set(target)
        for value in values:
            if value in existing:
                continue
            target.append(value)
            existing.add(value)
