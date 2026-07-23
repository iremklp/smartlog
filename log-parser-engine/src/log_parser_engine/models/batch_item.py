from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class BatchItem(BaseModel):
    """Immutable public record envelope for batch orchestration output."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    index: int
    source_line_start: int | None = None
    source_line_end: int | None = None
    raw_record: str | None = None
    raw_record_preview: str | None = None
    record_type: Literal["data", "header", "comment", "blank", "document"]
    context_attributes: dict[str, Any] = Field(default_factory=dict)
    character_count: int

    @field_validator("index")
    @classmethod
    def validate_index(cls, value: int) -> int:
        if value < 1:
            raise ValueError("index must be 1 or greater")
        return value

    @field_validator("source_line_start", "source_line_end")
    @classmethod
    def validate_line_numbers(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError("line numbers must be 1 or greater")
        return value

    @field_validator("character_count")
    @classmethod
    def validate_character_count(cls, value: int) -> int:
        if value < 0:
            raise ValueError("character_count must not be negative")
        return value

    @field_validator("raw_record", "raw_record_preview")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return str(value)

    @field_validator("context_attributes")
    @classmethod
    def copy_attributes(cls, value: dict[str, Any]) -> dict[str, Any]:
        return dict(value)

    @model_validator(mode="after")
    def validate_rules(self) -> "BatchItem":
        if self.source_line_start is None and self.source_line_end is not None:
            raise ValueError("source_line_end requires source_line_start")
        if (
            self.source_line_start is not None
            and self.source_line_end is not None
            and self.source_line_end < self.source_line_start
        ):
            raise ValueError("source_line_end must be >= source_line_start")

        if self.raw_record is None:
            if self.record_type == "blank" and self.character_count == 0:
                return self
            if self.raw_record_preview is None and self.character_count > 0:
                raise ValueError(
                    "raw_record_preview is required when raw_record is absent"
                )
            return self

        if len(self.raw_record) != self.character_count:
            raise ValueError("character_count must match raw_record length")

        if not self.raw_record and self.record_type != "blank":
            raise ValueError("empty raw_record is only valid for blank record_type")

        return self

    @property
    def line_span(self) -> int | None:
        if self.source_line_start is None or self.source_line_end is None:
            return None
        return self.source_line_end - self.source_line_start + 1
