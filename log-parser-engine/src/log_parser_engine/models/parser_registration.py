from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .enums import LogSourceType
from .parser_metadata import ParserMetadata


class ParserRegistration(BaseModel):
    """Immutable registration record for a parser in the registry."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    parser_name: str
    parser_version: str
    source_type: LogSourceType
    enabled: bool = True
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    registration_order: int = Field(default=0)
    metadata: ParserMetadata
    origin: str | None = None
    notes: str | None = None

    @field_validator("parser_name", "parser_version")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value must not be empty")
        return cleaned

    @field_validator("origin")
    @classmethod
    def normalize_origin(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        return cleaned or None

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("registration_order")
    @classmethod
    def validate_registration_order(cls, value: int) -> int:
        if value < 0:
            raise ValueError("registration_order must be 0 or greater")
        return value

    @field_validator("registered_at")
    @classmethod
    def normalize_registered_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("registered_at must be timezone-aware")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_registration_consistency(self) -> "ParserRegistration":
        normalized_name = self.metadata.name.strip().casefold()
        normalized_parser_name = self.parser_name.strip().casefold()
        if normalized_name != normalized_parser_name:
            raise ValueError("parser_name must match metadata.name")

        normalized_version = self.metadata.version.strip()
        if normalized_version != self.parser_version.strip():
            raise ValueError("parser_version must match metadata.version")

        if self.metadata.source_type != self.source_type:
            raise ValueError("source_type must match metadata.source_type")
        return self

    @property
    def identifier(self) -> str:
        return f"{self.parser_name}@{self.parser_version}"
