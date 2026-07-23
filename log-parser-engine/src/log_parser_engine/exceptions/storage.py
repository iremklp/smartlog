
"""Custom exceptions for the event store subsystem."""


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
    """
    Raised during a batch write operation, often containing partial results.
    
    Attributes:
        message (str): A summary of the batch failure.
        successful_writes (tuple): A tuple of events that were successfully written.
        failed_writes (tuple): A tuple of events that failed.
        errors (list[Exception]): A list of underlying exceptions for each failure.
    """
    def __init__(self, message, successful_writes=None, failed_writes=None, errors=None):
        super().__init__(message)
        self.successful_writes = successful_writes or ()
        self.failed_writes = failed_writes or ()
        self.errors = errors or []

