from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .batch_item_result import BatchItemResult
from .batch_parse_statistics import BatchParseStatistics
from .log_event import LogEvent
from .parser_session_info import ParserSessionInfo


class BatchParseResult(BaseModel):
    """Collected output for a batch parse execution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    events: tuple[LogEvent, ...] = Field(default_factory=tuple)
    failures: tuple[BatchItemResult, ...] = Field(default_factory=tuple)
    statistics: BatchParseStatistics
    sessions: tuple[ParserSessionInfo, ...] = Field(default_factory=tuple)
    warnings: tuple[str, ...] = Field(default_factory=tuple)
    source_id: str | None = None

    @field_validator("warnings")
    @classmethod
    def normalize_warnings(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized: list[str] = []
        for warning in value:
            cleaned = str(warning).strip()
            if cleaned:
                normalized.append(cleaned)
        return tuple(normalized)

    @field_validator("source_id")
    @classmethod
    def normalize_source_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @property
    def completed(self) -> bool:
        return not self.statistics.stopped_early

    @property
    def partial_success(self) -> bool:
        return (
            self.statistics.records_succeeded > 0 and self.statistics.records_failed > 0
        )

    @property
    def empty(self) -> bool:
        return self.statistics.records_seen == 0
