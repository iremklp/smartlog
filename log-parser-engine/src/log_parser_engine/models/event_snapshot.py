
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .stored_event import StoredEvent


class EventStoreSnapshot(BaseModel):
    """
    An immutable, serializable snapshot of the entire event store's state
    at a specific moment in time.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str = Field(default="1.0", description="The snapshot schema version.")
    created_at: datetime = Field(
        description="The UTC timestamp when the snapshot was created."
    )

    event_count: int = Field(description="The number of events in the snapshot.")
    events: tuple[StoredEvent, ...] = Field(
        description="The sequence of stored events."
    )

    content_hash: str = Field(
        description=(
            "A SHA-256 hash of the snapshot's content for integrity verification."
        )
    )
    estimated_size_bytes: int = Field(
        description="The total estimated size of all events in the snapshot."
    )

    metadata: dict[str, str | int | float] = Field(
        default_factory=dict,
        description="Optional metadata about the snapshot.",
    )
