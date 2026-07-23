
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .event_aggregation import EventAggregationRequest
from .event_filter import EventFilter
from .event_sort import EventSort


class EventQuery(BaseModel):
    """Defines a comprehensive query to execute against the event store."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    filter: EventFilter = Field(default_factory=EventFilter)
    sort: tuple[EventSort, ...] = Field(default_factory=tuple)
    offset: int = 0
    limit: int | None = None  # If None, store's default_page_size will be used

    include_events: bool = True
    include_total: bool = True
    
    include_facets: bool = False
    facet_fields: tuple[str, ...] = Field(default_factory=tuple)

    aggregation: EventAggregationRequest | None = None

    @field_validator("offset")
    @classmethod
    def _validate_offset(cls, value: int) -> int:
        if value < 0:
            raise ValueError("offset cannot be negative")
        return value

    @field_validator("limit")
    @classmethod
    def _validate_limit(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("limit cannot be negative")
        return value

    @field_validator("sort")
    @classmethod
    def _validate_sort(cls, value: tuple[EventSort, ...]) -> tuple[EventSort, ...]:
        seen_fields = set()
        for s in value:
            if s.field in seen_fields:
                raise ValueError(f"Duplicate sort field '{s.field}' is not allowed.")
            seen_fields.add(s.field)
        return value
    
    @field_validator("facet_fields")
    @classmethod
    def _normalize_facet_fields(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            return tuple()
        return tuple(sorted(list(set(item.strip() for item in value if item.strip()))))

