from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .enums import ParseStatus
from .log_event import LogEvent
from .parse_error import ParseError


class ParseResult(BaseModel):
    """Aggregate model for parser output."""

    model_config = ConfigDict(frozen=True)

    status: ParseStatus
    events: list[LogEvent] = Field(default_factory=list)
    errors: list[ParseError] = Field(default_factory=list)
