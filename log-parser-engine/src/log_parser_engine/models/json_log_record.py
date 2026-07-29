from __future__ import annotations

from copy import deepcopy

from pydantic import BaseModel, ConfigDict, Field, field_validator


class JsonLogRecord(BaseModel):
    """Immutable container for a parsed JSON log object."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    data: dict[str, object] = Field(default_factory=dict)
    raw_json: str
    profile: str = "generic"
    line_number: int | None = None
    additional_record_count: int = 0
    attributes: dict[str, object] = Field(default_factory=dict)

    @field_validator("raw_json")
    @classmethod
    def validate_raw_json(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("raw_json must not be empty")
        return cleaned

    @field_validator("profile")
    @classmethod
    def validate_profile(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("profile must not be empty")

        return cleaned

    @field_validator("line_number")
    @classmethod
    def validate_line_number(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError("line_number must be 1 or greater")
        return value

    @field_validator("additional_record_count")
    @classmethod
    def validate_additional_record_count(cls, value: int) -> int:
        if value < 0:
            raise ValueError("additional_record_count must not be negative")
        return value

    @field_validator("data")
    @classmethod
    def validate_data(cls, value: dict[str, object]) -> dict[str, object]:
        return deepcopy(value)

    @field_validator("attributes")
    @classmethod
    def validate_attributes(cls, value: dict[str, object]) -> dict[str, object]:
        return deepcopy(value)

    @property
    def field_count(self) -> int:
        return len(self.data)

    @property
    def has_additional_records(self) -> bool:
        return self.additional_record_count > 0

    @property
    def top_level_keys(self) -> tuple[str, ...]:
        return tuple(self.data.keys())
