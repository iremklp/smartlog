from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IisW3CRecord(BaseModel):
    """Immutable IIS W3C record parsed from a single data line."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    fields: dict[str, str | None] = Field(default_factory=dict)
    field_order: tuple[str, ...] = Field(default_factory=tuple)
    raw_line: str
    line_number: int | None = None
    extra_values: tuple[str, ...] = Field(default_factory=tuple)
    missing_fields: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("raw_line")
    @classmethod
    def validate_raw_line(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("raw_line must not be empty")
        return cleaned

    @field_validator("line_number")
    @classmethod
    def validate_line_number(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError("line_number must be 1 or greater")
        return value

    @field_validator("fields")
    @classmethod
    def validate_fields(cls, value: dict[str, str | None]) -> dict[str, str | None]:
        return dict(value)

    @field_validator("field_order")
    @classmethod
    def validate_field_order(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            str(field).strip().lower()
            for field in value
            if str(field).strip()
        )

    @property
    def complete(self) -> bool:
        return not self.missing_fields and not self.extra_values

    def get(self, field_name: str) -> str | None:
        return self.fields.get(str(field_name).strip().lower())

    @property
    def value_count(self) -> int:
        return len(self.fields)
