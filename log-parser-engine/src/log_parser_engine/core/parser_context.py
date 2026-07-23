from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ParserContext(BaseModel):
    """Immutable execution context passed to parsers at runtime."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_name: str | None = None
    file_path: str | None = None
    content_type: str | None = None
    encoding: str = "utf-8"
    line_number: int | None = None
    environment: str | None = None
    application: str | None = None
    service: str | None = None
    host: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    strict: bool = False
    preserve_raw: bool = True

    @field_validator(
        "source_name",
        "file_path",
        "content_type",
        "environment",
        "application",
        "service",
        "host",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("content_type")
    @classmethod
    def normalize_content_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        return cleaned or None

    @field_validator("encoding")
    @classmethod
    def validate_encoding(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("encoding must not be empty")
        return cleaned

    @field_validator("line_number")
    @classmethod
    def validate_line_number(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError("line_number must be 1 or greater")
        return value

    @field_validator("attributes")
    @classmethod
    def validate_attributes(cls, value: dict[str, Any]) -> dict[str, Any]:
        return dict(value)

    def with_line_number(self, line_number: int) -> "ParserContext":
        return self.model_copy(update={"line_number": line_number})
