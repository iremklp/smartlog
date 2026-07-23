from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class BatchParseStatistics(BaseModel):
    """Immutable statistics summary for a batch parse execution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    records_seen: int = 0
    records_attempted: int = 0
    records_succeeded: int = 0
    records_failed: int = 0
    records_skipped: int = 0
    headers_seen: int = 0
    comments_seen: int = 0
    blank_records_seen: int = 0
    events_collected: int = 0
    failures_collected: int = 0
    failures_dropped: int = 0
    parser_detection_count: int = 0
    parser_redetection_count: int = 0
    parser_switch_count: int = 0
    bytes_or_characters_processed: int = 0
    max_record_characters_seen: int = 0
    total_duration_ms: float = 0.0
    detection_duration_ms: float = 0.0
    parsing_duration_ms: float = 0.0
    earliest_event_timestamp: datetime | None = None
    latest_event_timestamp: datetime | None = None
    stopped_early: bool = False
    stop_reason: str | None = None
    parser_counts: dict[str, int] = Field(default_factory=dict)
    error_counts: dict[str, int] = Field(default_factory=dict)
    status_counts: dict[str, int] = Field(default_factory=dict)

    @field_validator(
        "records_seen",
        "records_attempted",
        "records_succeeded",
        "records_failed",
        "records_skipped",
        "headers_seen",
        "comments_seen",
        "blank_records_seen",
        "events_collected",
        "failures_collected",
        "failures_dropped",
        "parser_detection_count",
        "parser_redetection_count",
        "parser_switch_count",
        "bytes_or_characters_processed",
        "max_record_characters_seen",
    )
    @classmethod
    def validate_non_negative_counts(cls, value: int) -> int:
        if value < 0:
            raise ValueError("count values must not be negative")
        return value

    @field_validator(
        "total_duration_ms", "detection_duration_ms", "parsing_duration_ms"
    )
    @classmethod
    def validate_durations(cls, value: float) -> float:
        if value < 0:
            raise ValueError("duration values must not be negative")
        return value

    @field_validator("stop_reason")
    @classmethod
    def normalize_stop_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("parser_counts", "error_counts", "status_counts")
    @classmethod
    def copy_count_maps(cls, value: dict[str, int]) -> dict[str, int]:
        copied = {str(key): int(count) for key, count in value.items()}
        for count in copied.values():
            if count < 0:
                raise ValueError("dictionary count values must not be negative")
        return copied

    @field_validator("earliest_event_timestamp", "latest_event_timestamp")
    @classmethod
    def validate_timestamps(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_rules(self) -> "BatchParseStatistics":
        if self.records_succeeded + self.records_failed > self.records_attempted:
            raise ValueError("attempted record counts are inconsistent")
        if self.stopped_early and self.stop_reason is None:
            raise ValueError("stop_reason is required when stopped_early is true")
        if (
            self.earliest_event_timestamp is not None
            and self.latest_event_timestamp is not None
            and self.earliest_event_timestamp > self.latest_event_timestamp
        ):
            raise ValueError(
                "earliest_event_timestamp must be <= latest_event_timestamp"
            )
        return self

    @property
    def success_rate(self) -> float | None:
        if self.records_attempted == 0:
            return None
        return self.records_succeeded / self.records_attempted

    @property
    def error_rate(self) -> float | None:
        if self.records_attempted == 0:
            return None
        return self.records_failed / self.records_attempted

    @property
    def average_parse_duration_ms(self) -> float | None:
        if self.records_attempted == 0:
            return None
        return self.parsing_duration_ms / self.records_attempted
