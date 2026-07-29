from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Literal

from log_parser_engine.models import StoredEvent


def determine_expired_event_ids(
    events: Iterable[StoredEvent],
    *,
    now: datetime,
    retention_seconds: int,
    basis: Literal["inserted_at", "event_timestamp"],
) -> tuple[str, ...]:
    """Return event IDs older than the configured retention boundary."""

    if (
        now.tzinfo is None
        or now.utcoffset() != timezone.utc.utcoffset(None)
    ):
        raise ValueError("'now' must be an aware UTC datetime")

    expired_ids: list[str] = []
    for event in events:
        timestamp = (
            event.inserted_at
            if basis == "inserted_at"
            else event.timestamp
        )
        if (now - timestamp).total_seconds() > retention_seconds:
            expired_ids.append(event.id)
    return tuple(expired_ids)


def get_eviction_candidates(
    *,
    num_to_evict: int,
    policy: str,
    sequence_ids: list[str],
    timestamp_index: list[tuple[datetime, int, str]],
) -> tuple[str, ...]:
    """Return deterministic candidate IDs for a supported eviction policy."""

    if num_to_evict <= 0:
        return ()
    if policy == "oldest_inserted":
        return tuple(sequence_ids[:num_to_evict])
    if policy == "oldest_event_timestamp":
        return tuple(
            item[2]
            for item in timestamp_index[:num_to_evict]
        )
    if policy == "reject_new":
        return ()
    raise ValueError(f"Unknown eviction policy: {policy}")
