from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator


class BatchProgress(BaseModel):
    """Progress snapshot exposed to caller callbacks."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    records_seen: int
    records_succeeded: int
    records_failed: int
    records_skipped: int
    current_parser: str | None = None
    elapsed_ms: float
    success_rate: float | None = None
    error_rate: float | None = None
    source_line: int | None = None
    source_id: str | None = None

    @field_validator(
        "records_seen",
        "records_succeeded",
        "records_failed",
        "records_skipped",
        "source_line",
    )
    @classmethod
    def validate_non_negative(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value < 0:
            raise ValueError("count values must not be negative")
        return value

    @field_validator("elapsed_ms")
    @classmethod
    def validate_elapsed_ms(cls, value: float) -> float:
        if value < 0:
            raise ValueError("elapsed_ms must not be negative")
        return value

    @field_validator("current_parser", "source_id")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("success_rate", "error_rate")
    @classmethod
    def validate_rates(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if not 0.0 <= value <= 1.0:
            raise ValueError("rate must be between 0.0 and 1.0")
        return value
