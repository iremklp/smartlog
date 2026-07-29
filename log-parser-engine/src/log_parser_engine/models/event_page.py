from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EventPage(BaseModel):
    """Describe pagination for one deterministic query snapshot."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    offset: int = Field(
        ge=0,
        description="Starting offset of the returned page.",
    )
    limit: int = Field(
        ge=1,
        description="Maximum number of items requested for the page.",
    )
    returned: int = Field(
        ge=0,
        description="Actual number of events selected for this page.",
    )
    total: int | None = Field(
        ge=0,
        description="Total matching events when requested.",
    )

    @property
    def has_more(self) -> bool:
        """Return whether another page may exist."""

        if self.total is None:
            return self.returned == self.limit
        return self.offset + self.returned < self.total

    @property
    def next_offset(self) -> int | None:
        """Return the next offset, or None when this is the last page."""

        if not self.has_more:
            return None
        return self.offset + self.returned

    @model_validator(mode="after")
    def _validate_counts(self) -> EventPage:
        if self.returned > self.limit:
            raise ValueError(
                "returned count cannot be greater than the limit"
            )
        if self.total is not None and self.returned > self.total:
            raise ValueError(
                "returned count cannot be greater than the total"
            )
        return self
