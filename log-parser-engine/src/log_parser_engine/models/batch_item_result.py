from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .batch_item import BatchItem
from .log_event import LogEvent
from .parse_result import ParseResult
from .enums import ParseStatus


class BatchItemResult(BaseModel):
    """Immutable result emitted per logical batch item."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    item: BatchItem
    status: Literal["success", "failure", "skipped", "header", "comment"]
    parser_name: str | None = None
    event: LogEvent | None = None
    parse_result: ParseResult | None = None
    error_code: str | None = None
    error_message: str | None = None
    duration_ms: float | None = None
    detection_performed: bool = False
    redetection_performed: bool = False
    state_updates: dict[str, Any] = Field(default_factory=dict)
    attributes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("parser_name", "error_code", "error_message")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @field_validator("duration_ms")
    @classmethod
    def validate_duration(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("duration_ms must not be negative")
        return value

    @field_validator("state_updates", "attributes")
    @classmethod
    def copy_dicts(cls, value: dict[str, Any]) -> dict[str, Any]:
        return dict(value)

    @model_validator(mode="after")
    def validate_rules(self) -> "BatchItemResult":
        if self.status == "success":
            if self.parse_result is None or self.parse_result.status != ParseStatus.success:
                raise ValueError("success status requires successful parse_result")
            if self.error_code is not None or self.error_message is not None:
                raise ValueError("success status cannot include error fields")

        if self.status == "failure":
            has_parse_failure = (
                self.parse_result is not None and self.parse_result.status != ParseStatus.success
            )
            has_error_text = self.error_code is not None or self.error_message is not None
            if not has_parse_failure and not has_error_text:
                raise ValueError("failure status requires parse failure or error info")

        if self.status in {"skipped", "header", "comment"}:
            if self.event is not None:
                raise ValueError("non-data statuses cannot include an event")

        return self
