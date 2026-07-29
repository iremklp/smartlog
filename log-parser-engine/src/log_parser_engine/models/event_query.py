from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .event_aggregation import EventAggregationRequest
from .event_filter import EventFilter
from .event_sort import EventSort

FacetField = Literal[
    "severity",
    "source_type",
    "event_type",
    "parser_name",
    "host",
    "service",
    "tags",
]


class EventQuery(BaseModel):
    """Define a bounded, typed query against an event store snapshot."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    filter: EventFilter = Field(default_factory=EventFilter)
    sort: tuple[EventSort, ...] = Field(default_factory=tuple)
    offset: int = Field(default=0, ge=0)
    limit: int | None = Field(default=None, ge=1)

    include_events: bool = True
    include_total: bool = True
    include_facets: bool = False
    facet_fields: tuple[FacetField, ...] = Field(default_factory=tuple)
    aggregation: EventAggregationRequest | None = None

    @field_validator("sort")
    @classmethod
    def _validate_sort(
        cls,
        value: tuple[EventSort, ...],
    ) -> tuple[EventSort, ...]:
        seen_fields: set[str] = set()
        for criterion in value:
            if criterion.field in seen_fields:
                raise ValueError(
                    f"Duplicate sort field '{criterion.field}' is not allowed."
                )
            seen_fields.add(criterion.field)
        return value

    @field_validator("facet_fields")
    @classmethod
    def _normalize_facet_fields(
        cls,
        value: tuple[FacetField, ...],
    ) -> tuple[FacetField, ...]:
        return tuple(dict.fromkeys(value))
