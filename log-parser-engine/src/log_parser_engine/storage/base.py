
from __future__ import annotations

from typing import Iterable, Protocol

from log_parser_engine.models import (
    BatchWriteResult,
    EventQuery,
    EventQueryResult,
    EventStoreStatistics,
    EventWriteResult,
    LogEvent,
    StoredEvent,
)

from .options import BatchWriteOptions, EventWriteOptions


class EventStore(Protocol):
    """
    Protocol defining the standard interface for an event storage and query system.
    """

    def add(
        self,
        event: LogEvent,
        *,
        options: EventWriteOptions | None = None,
    ) -> EventWriteResult:
        """
        Adds a single log event to the store.

        Args:
            event: The LogEvent to add.
            options: Per-call write options.

        Returns:
            An EventWriteResult detailing the outcome.
        """
        ...

    def add_many(
        self,
        events: Iterable[LogEvent],
        *,
        options: EventWriteOptions | None = None,
        batch_options: BatchWriteOptions | None = None,
    ) -> BatchWriteResult:
        """
        Adds multiple log events to the store.

        Args:
            events: An iterable of LogEvents to add.
            options: Per-call write options applied to each event.
            batch_options: Options governing the batch operation itself.

        Returns:
            A BatchWriteResult summarizing the outcome of the entire batch.
        """
        ...

    def get(
        self,
        event_id: str,
    ) -> StoredEvent | None:
        """
        Retrieves a single stored event by its unique ID.

        Args:
            event_id: The ID of the event to retrieve.

        Returns:
            The StoredEvent if found, otherwise None.
        """
        ...

    def query(
        self,
        query: EventQuery | None = None,
    ) -> EventQueryResult:
        """

        Executes a query against the event store.

        Args:
            query: An EventQuery object defining filter, sort, and pagination.
                   If None, a default query is executed.

        Returns:
            An EventQueryResult containing the results.
        """
        ...

    def delete(
        self,
        event_id: str,
    ) -> bool:
        """
        Deletes a single event from the store by its ID.

        Args:
            event_id: The ID of the event to delete.

        Returns:
            True if the event was found and deleted, False otherwise.
        """
        ...

    def clear(self) -> int:
        """
        Removes all events from the store.

        Returns:
            The number of events removed.
        """
        ...

    def count(self) -> int:
        """
        Returns the total number of events currently in the store.

        Returns:
            The total event count.
        """
        ...

    def statistics(self) -> EventStoreStatistics:
        """
        Retrieves runtime statistics about the event store.

        Returns:
            An EventStoreStatistics object.
        """
        ...
