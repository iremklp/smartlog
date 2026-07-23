
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Literal

from log_parser_engine.models import StoredEvent

from .options import EventStoreOptions


def determine_expired_event_ids(
    events: Iterable[StoredEvent],
    *,
    now: datetime,
    retention_seconds: int,
    basis: Literal["inserted_at", "event_timestamp"],
) -> tuple[str, ...]:
    """
    Determines which events have expired based on the retention policy.

    Args:
        events: An iterable of StoredEvents to evaluate.
        now: The current UTC time to compare against.
        retention_seconds: The maximum age of an event in seconds.
        basis: The timestamp field to use for the age calculation.

    Returns:
        A tuple of event IDs that are considered expired.
    """
    if now.tzinfo is None or now.tzinfo.utcoffset(now) != timezone.utc.utcoffset(None):
        raise ValueError("'now' must be an aware UTC datetime")

    expired_ids = []
    for event in events:
        timestamp_to_check = event.inserted_at if basis == "inserted_at" else event.timestamp
        age = now - timestamp_to_check
        if age.total_seconds() > retention_seconds:
            expired_ids.append(event.id)
    
    return tuple(expired_ids)


def get_eviction_candidates(
    *,
    num_to_evict: int,
    policy: str,
    sequence_ids: list[str],
    timestamp_index: list[tuple[datetime, int, str]],
) -> tuple[str, ...]:
    """
    Determines which events to evict based on the eviction policy.

    Args:
        num_to_evict: The number of events that need to be removed.
        policy: The eviction policy to apply.
        sequence_ids: A list of event IDs ordered by insertion sequence.
        timestamp_index: A list of (timestamp, seq, id) tuples, sorted by timestamp.

    Returns:
        A tuple of event IDs to evict.
    """
    if num_to_evict <= 0:
        return tuple()

    if policy == "oldest_inserted":
        return tuple(sequence_ids[:num_to_evict])
    
    if policy == "oldest_event_timestamp":
        # The timestamp index is already sorted by (timestamp, sequence)
        return tuple(item[2] for item in timestamp_index[:num_to_evict])

    if policy == "reject_new":
        # This policy means we don't evict, but the caller should raise an error.
        return tuple()
        
    raise ValueError(f"Unknown eviction policy: {policy}")
