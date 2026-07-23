from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from log_parser_engine.models import BatchItemResult, BatchParseStatistics

from .helpers import update_min_max_timestamps


@dataclass(slots=True)
class StatisticsTracker:
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
    parser_counts: dict[str, int] = field(default_factory=dict)
    error_counts: dict[str, int] = field(default_factory=dict)
    status_counts: dict[str, int] = field(default_factory=dict)

    def observe_result(self, result: BatchItemResult) -> None:
        self.records_seen += 1
        self.bytes_or_characters_processed += result.item.character_count
        self.max_record_characters_seen = max(
            self.max_record_characters_seen,
            result.item.character_count,
        )
        self.status_counts[result.status] = self.status_counts.get(result.status, 0) + 1

        if result.item.record_type == "blank":
            self.blank_records_seen += 1

        if result.status == "success":
            self.records_attempted += 1
            self.records_succeeded += 1
            if result.parser_name is not None:
                self.parser_counts[result.parser_name] = (
                    self.parser_counts.get(result.parser_name, 0) + 1
                )
            if result.event is not None:
                self.earliest_event_timestamp, self.latest_event_timestamp = (
                    update_min_max_timestamps(
                        self.earliest_event_timestamp,
                        self.latest_event_timestamp,
                        result.event.timestamp,
                    )
                )
        elif result.status == "failure":
            self.records_attempted += 1
            self.records_failed += 1
            code = result.error_code or "PARSE_FAILED"
            self.error_counts[code] = self.error_counts.get(code, 0) + 1
            if result.parser_name is not None:
                self.parser_counts[result.parser_name] = (
                    self.parser_counts.get(result.parser_name, 0) + 1
                )
        elif result.status == "skipped":
            self.records_skipped += 1
        elif result.status == "header":
            self.headers_seen += 1
        elif result.status == "comment":
            self.comments_seen += 1

        if result.duration_ms is not None:
            self.parsing_duration_ms += result.duration_ms

    def snapshot(self) -> BatchParseStatistics:
        return BatchParseStatistics(
            records_seen=self.records_seen,
            records_attempted=self.records_attempted,
            records_succeeded=self.records_succeeded,
            records_failed=self.records_failed,
            records_skipped=self.records_skipped,
            headers_seen=self.headers_seen,
            comments_seen=self.comments_seen,
            blank_records_seen=self.blank_records_seen,
            events_collected=self.events_collected,
            failures_collected=self.failures_collected,
            failures_dropped=self.failures_dropped,
            parser_detection_count=self.parser_detection_count,
            parser_redetection_count=self.parser_redetection_count,
            parser_switch_count=self.parser_switch_count,
            bytes_or_characters_processed=self.bytes_or_characters_processed,
            max_record_characters_seen=self.max_record_characters_seen,
            total_duration_ms=self.total_duration_ms,
            detection_duration_ms=self.detection_duration_ms,
            parsing_duration_ms=self.parsing_duration_ms,
            earliest_event_timestamp=self.earliest_event_timestamp,
            latest_event_timestamp=self.latest_event_timestamp,
            stopped_early=self.stopped_early,
            stop_reason=self.stop_reason,
            parser_counts=dict(self.parser_counts),
            error_counts=dict(self.error_counts),
            status_counts=dict(self.status_counts),
        )
