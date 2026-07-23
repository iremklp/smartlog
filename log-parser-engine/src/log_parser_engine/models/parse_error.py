from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from .enums import ErrorType, ParseStatus


class ParseError(BaseModel):
    """Represents a parse failure or validation issue."""

    model_config = ConfigDict(frozen=True)

    message: str
    status: ParseStatus = ParseStatus.FAILED
    error_type: ErrorType = ErrorType.UNKNOWN_FORMAT
    details: dict[str, str] | None = None

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("message must not be empty")
        return cleaned
