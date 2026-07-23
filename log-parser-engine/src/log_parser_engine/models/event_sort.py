
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SORT_FIELDS = Literal[
    "timestamp",
    "inserted_at",
    "sequence",
    "severity",
    "event_type",
    "host",
]
SORT_DIRECTIONS = Literal["asc", "desc"]


class EventSort(BaseModel):
    """Defines a single sort criterion for an event query."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    field: SORT_FIELDS = Field(description="The field to sort by.")
    direction: SORT_DIRECTIONS = Field(description="The sort direction.")
