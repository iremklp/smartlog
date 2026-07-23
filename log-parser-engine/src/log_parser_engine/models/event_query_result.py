
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .event_aggregation import EventAggregationResult
from .event_page import EventPage
from .stored_event import StoredEvent


class FacetBucket(BaseModel):
    """Represents a single bucket within a facet result."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    value: str
    count: int


class EventQueryResult(BaseModel):
    """Represents the complete result of an `EventQuery`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    events: tuple[StoredEvent, ...] = Field(description="The sequence of events matching the query for the given page.")
    page: EventPage = Field(description="Pagination details for the result set.")
    
    facets: dict[str, tuple[FacetBucket, ...]] = Field(
        default_factory=dict,
        description="Facet results, keyed by field name."
    )
    aggregation: EventAggregationResult | None = Field(
        default=None,
        description="Aggregation results, if requested."
    )
    
    query_duration_ms: float = Field(description="The total time taken to execute the query in milliseconds.")
    snapshot_size: int = Field(description="The number of events in the data snapshot processed by the query.")
    index_used: bool = Field(description="Indicates if secondary indexes were used to optimize the query.")
    candidate_count: int = Field(description="Number of potential candidates after initial filtering (e.g., from indexes).")
    
    warnings: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Any warnings generated during query execution."
    )
