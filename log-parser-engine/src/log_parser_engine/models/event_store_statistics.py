
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EventStoreStatistics(BaseModel):
    """A snapshot of the event store's runtime statistics."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_count: int
    estimated_memory_bytes: int

    max_events: int
    max_estimated_memory_bytes: int | None

    oldest_inserted_at: datetime | None
    newest_inserted_at: datetime | None
    earliest_event_timestamp: datetime | None
    latest_event_timestamp: datetime | None

    index_enabled: bool
    indexed_field_count: int

    duplicate_ignored_count: int
    replaced_count: int
    evicted_count: int
    retention_removed_count: int

    write_count: int
    query_count: int
    delete_count: int
    clear_count: int

    created_at: datetime
    last_write_at: datetime | None
    last_query_at: datetime | None
    last_retention_at: datetime | None
