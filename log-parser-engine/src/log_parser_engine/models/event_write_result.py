
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .stored_event import StoredEvent

WRITE_STATUS = Literal["inserted", "ignored_duplicate", "replaced"]


class EventWriteResult(BaseModel):
    """Result of a single `add` operation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: WRITE_STATUS
    stored_event: StoredEvent
    evicted_event_ids: tuple[str, ...] = Field(default_factory=tuple)


class BatchWriteResult(BaseModel):
    """Result of a batch `add_many` operation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    inserted: tuple[StoredEvent, ...] = Field(default_factory=tuple)
    ignored_event_ids: tuple[str, ...] = Field(default_factory=tuple)
    replaced: tuple[StoredEvent, ...] = Field(default_factory=tuple)
    evicted_event_ids: tuple[str, ...] = Field(default_factory=tuple)
    errors: tuple[str, ...] = Field(default_factory=tuple) # Storing only error messages for security
    atomic: bool

    @property
    def was_successful(self) -> bool:
        """Returns true if the entire batch was processed without any errors."""
        return not self.errors

    @property
    def was_partial_success(self) -> bool:
        """
        Returns true if there were no errors in a non-atomic operation,
        or if there were some successes alongside errors.
        """
        return self.inserted_count > 0 and not self.errors

    @property
    def inserted_count(self) -> int:
        """Number of new events inserted."""
        return len(self.inserted)
    
    @property
    def replaced_count(self) -> int:
        """Number of events that were replaced."""
        return len(self.replaced)

    @property
    def error_count(self) -> int:
        """Number of errors encountered."""
        return len(self.errors)

    @property
    def ignored_count(self) -> int:
        """Number of duplicate events that were ignored."""
        return len(self.ignored_event_ids)
    
    @property
    def evicted_count(self) -> int:
        """Number of events that were evicted to make space."""
        return len(self.evicted_event_ids)
