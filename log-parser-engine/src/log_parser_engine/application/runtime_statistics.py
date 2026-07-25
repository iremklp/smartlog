from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from log_parser_engine.models import EventStoreStatistics


class ApplicationRuntimeStatistics(BaseModel):
    """Runtime snapshot for the application service."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    created_at: datetime
    observed_at: datetime
    uptime_ms: float
    parser_count: int
    enabled_parser_count: int
    store_statistics: EventStoreStatistics
    startup_warnings: tuple[str, ...] = Field(default_factory=tuple)