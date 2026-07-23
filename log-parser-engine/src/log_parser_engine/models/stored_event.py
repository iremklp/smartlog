
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import LogSeverity
from .log_event import LogEvent


class StoredEvent(BaseModel):
    """
    Immutable model representing a log event as it is stored in the event store.

    It wraps the original `LogEvent` and adds storage-specific metadata.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(description="The unique identifier of the event in the store.")
    event: LogEvent = Field(description="The original, immutable log event.")
    inserted_at: datetime = Field(description="The UTC timestamp when the event was inserted into the store.")
    sequence: int = Field(description="A monotonically increasing sequence number for insertion order.")
    content_hash: str = Field(description="The SHA-256 hash of the canonical event content.")
    estimated_size_bytes: int = Field(description="The estimated memory size of the event in bytes.")
    source_batch_id: str | None = Field(
        default=None,
        description="The identifier of the batch this event originated from.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom metadata associated with the stored event.",
    )

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("id must not be empty")
        return value

    @field_validator("inserted_at")
    @classmethod
    def _validate_inserted_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.tzinfo.utcoffset(value) != timezone.utc.utcoffset(None):
            raise ValueError("inserted_at must be an aware UTC datetime")
        return value

    @field_validator("sequence")
    @classmethod
    def _validate_sequence(cls, value: int) -> int:
        if value < 1:
            raise ValueError("sequence must be greater than or equal to 1")
        return value

    @field_validator("content_hash")
    @classmethod
    def _validate_hash(cls, value: str) -> str:
        # Basic validation for a hex digest. A full regex is overkill.
        if len(value) != 64 or not all(c in "0123456789abcdef" for c in value):
            raise ValueError("content_hash must be a 64-character lowercase SHA-256 hex digest")
        return value

    @field_validator("estimated_size_bytes")
    @classmethod
    def _validate_size(cls, value: int) -> int:
        if value < 0:
            raise ValueError("estimated_size_bytes must not be negative")
        return value
    
    @field_validator("metadata")
    @classmethod
    def _defensive_copy_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        return value.copy()

    # --- Convenience Properties to access underlying event data ---

    @property
    def timestamp(self) -> datetime:
        """The timestamp of the original event."""
        return self.event.timestamp

    @property
    def severity(self) -> LogSeverity:
        """The severity of the original event."""
        return self.event.severity

    @property
    def event_type(self) -> str | None:
        """The event type of the original event."""
        return self.event.event_type
