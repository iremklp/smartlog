from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .event_aggregation import EventAggregationResult
from .event_page import EventPage
from .immutable import FrozenDict
from .stored_event import StoredEvent


class FacetBucket(BaseModel):
    """Represent one value/count pair in a facet."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    value: str
    count: int = Field(ge=0)


class EventQueryResult(BaseModel):
    """Represent an immutable result for one event snapshot query."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    events: tuple[StoredEvent, ...] = Field(default_factory=tuple)
    page: EventPage
    facets: dict[str, tuple[FacetBucket, ...]] = Field(
        default_factory=FrozenDict,
    )
    aggregation: EventAggregationResult | None = None
    query_duration_ms: float = Field(ge=0)
    snapshot_size: int = Field(ge=0)
    index_used: bool
    candidate_count: int = Field(ge=0)
    warnings: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("facets")
    @classmethod
    def _freeze_facets(
        cls,
        value: dict[str, tuple[FacetBucket, ...]],
    ) -> dict[str, tuple[FacetBucket, ...]]:
        return FrozenDict(
            {
                field: tuple(buckets)
                for field, buckets in value.items()
            }
        )
