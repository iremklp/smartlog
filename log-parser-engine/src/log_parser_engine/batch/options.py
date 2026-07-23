from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class BatchParseOptions(BaseModel):
    """Immutable options controlling batch parse orchestration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    record_mode: str = "auto"
    parser_name: str | None = None
    detect_once: bool = True
    redetect_on_failure: bool = False
    redetect_interval: int | None = None
    detection_sample_size: int = 20
    max_detection_sample_characters: int = Field(default=1024 * 1024)
    max_records: int | None = None
    max_record_characters: int = Field(default=1024 * 1024)
    max_buffered_results: int = 1000
    collect_events: bool = True
    collect_failures: bool = True
    max_collected_events: int | None = None
    max_collected_failures: int = 1000
    stop_on_error: bool = False
    max_errors: int | None = None
    max_consecutive_errors: int | None = 100
    error_rate_threshold: float | None = None
    error_rate_minimum_records: int = 100
    skip_blank_records: bool = True
    preserve_blank_records: bool = False
    include_raw_record_in_result: bool = False
    include_success_event: bool = True
    include_failure_details: bool = True
    progress_interval_records: int = 1000
    strict: bool = False
    parser_strict: bool | None = None
    stateful_header_mode: bool = True
    allow_mixed_formats: bool = False
    mixed_format_redetection_window: int = 5
    timing_enabled: bool = True
    source_id: str | None = None
    follow_symlinks: bool = False
    allow_empty_source: bool = True
    raise_fatal_errors: bool = False

    @field_validator("record_mode")
    @classmethod
    def validate_record_mode(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned not in {"auto", "line", "multiline_document"}:
            raise ValueError("record_mode must be auto, line, or multiline_document")
        return cleaned

    @field_validator("parser_name", "source_id")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator(
        "detection_sample_size",
        "max_detection_sample_characters",
        "max_record_characters",
        "max_buffered_results",
        "max_collected_failures",
        "error_rate_minimum_records",
        "progress_interval_records",
        "mixed_format_redetection_window",
    )
    @classmethod
    def validate_positive_ints(cls, value: int) -> int:
        if value < 1:
            raise ValueError("value must be 1 or greater")
        return value

    @field_validator(
        "max_records",
        "max_collected_events",
        "max_errors",
        "max_consecutive_errors",
        "redetect_interval",
    )
    @classmethod
    def validate_optional_positive_ints(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value < 1:
            raise ValueError("value must be 1 or greater")
        return value

    @field_validator("error_rate_threshold")
    @classmethod
    def validate_threshold(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if not 0.0 <= value <= 1.0:
            raise ValueError("error_rate_threshold must be between 0.0 and 1.0")
        return value

    @model_validator(mode="after")
    def validate_option_rules(self) -> "BatchParseOptions":
        if self.preserve_blank_records and self.skip_blank_records:
            raise ValueError("preserve_blank_records requires skip_blank_records=False")
        if self.redetect_on_failure and not self.allow_mixed_formats:
            raise ValueError("redetect_on_failure requires allow_mixed_formats=True")
        if self.record_mode == "multiline_document" and self.detect_once is False:
            raise ValueError("multiline_document mode requires detect_once=True")
        return self
