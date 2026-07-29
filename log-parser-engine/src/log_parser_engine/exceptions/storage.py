
"""Custom exceptions for the event store subsystem."""

from __future__ import annotations

from collections.abc import Iterable


class EventStoreError(Exception):
    """Base exception for all event store errors."""


class EventStoreConfigurationError(EventStoreError):
    """Raised for configuration-related errors."""


class InvalidEventError(EventStoreError):
    """Raised when an event is invalid for storage."""


class InvalidEventIdError(InvalidEventError):
    """Raised for issues related to event IDs."""


class DuplicateEventError(InvalidEventIdError):
    """Raised when a duplicate event is rejected."""


class EventIdCollisionError(InvalidEventIdError):
    """
    Raised when two distinct events map to the same ID, which is a rare
    but possible hash collision.
    """


class EventStoreCapacityError(EventStoreError):
    """Raised when the store's capacity limits are breached."""


class EventTooLargeForStoreError(EventStoreCapacityError):
    """
    Raised when a single event is larger than the store's total memory limit.
    """


class EventQueryError(EventStoreError):
    """Base exception for query-related errors."""


class EventFilterError(EventQueryError):
    """Raised for invalid filter criteria."""


class EventSortError(EventQueryError):
    """Raised for invalid sort criteria."""


class EventPaginationError(EventQueryError):
    """Raised for invalid pagination parameters."""


class EventAggregationError(EventQueryError):
    """Raised for invalid aggregation requests."""


class EventSnapshotError(EventStoreError):
    """Raised for errors related to creating or restoring snapshots."""


class BatchWriteError(EventStoreError):
    """Raised when a batch cannot be prepared or safely processed."""

    def __init__(
        self,
        message: str,
        successful_writes: Iterable[object] | None = None,
        failed_writes: Iterable[object] | None = None,
        errors: Iterable[Exception] | None = None,
    ) -> None:
        super().__init__(message)
        self.successful_writes = tuple(successful_writes or ())
        self.failed_writes = tuple(failed_writes or ())
        self.errors = tuple(errors or ())
