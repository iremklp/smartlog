
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EventPage(BaseModel):
    """Describes the pagination state of an event query result."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    offset: int = Field(description="The starting offset of the returned page.")
    limit: int = Field(description="The maximum number of items requested for the page.")
    returned: int = Field(description="The actual number of events returned on this page.")
    total: int | None = Field(description="The total number of events matching the query, if requested.")

    @property
    def has_more(self) -> bool:
        """True if there are more events available beyond the current page."""
        if self.total is None:
            # If total is unknown, we assume there might be more if we received a full page.
            return self.returned == self.limit
        return (self.offset + self.returned) < self.total

    @property
    def next_offset(self) -> int | None:
        """The offset for the next page of results, or None if this is the last page."""
        if not self.has_more:
            return None
        return self.offset + self.returned

    @model_validator(mode="after")
    def _validate_page_logic(self) -> "EventPage":
        if self.offset < 0:
            raise ValueError("offset cannot be negative")
        if self.limit < 0:
            raise ValueError("limit cannot be negative")
        if self.returned < 0:
            raise ValueError("returned count cannot be negative")
        if self.total is not None and self.total < 0:
            raise ValueError("total count cannot be negative")
        if self.returned > self.limit:
            raise ValueError("returned count cannot be greater than the limit")
        if self.total is not None and self.returned > self.total:
            raise ValueError("returned count cannot be greater than the total")

        return self
