from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class IngestionSource(BaseModel):
    """Immutable description of a single ingested source."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["path", "bytes", "text", "archive_entry"]
    name: str | None = None
    path: str | None = None
    extension: str | None = None
    content_type: str | None = None
    archive_name: str | None = None
    archive_entry_name: str | None = None
    size_bytes: int
    modified_at: datetime | None = None

    @field_validator("name", "path", "archive_name", "archive_entry_name")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("extension")
    @classmethod
    def normalize_extension(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        if not cleaned:
            return None
        return cleaned[1:] if cleaned.startswith(".") else cleaned

    @field_validator("content_type")
    @classmethod
    def normalize_content_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        if not cleaned:
            return None
        return cleaned.split(";", 1)[0].strip()

    @field_validator("size_bytes")
    @classmethod
    def validate_size_bytes(cls, value: int) -> int:
        if value < 0:
            raise ValueError("size_bytes must not be negative")
        return value

    @field_validator("modified_at")
    @classmethod
    def validate_modified_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("modified_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_archive_consistency(self) -> "IngestionSource":
        if self.kind == "archive_entry":
            if not self.archive_name or not self.archive_entry_name:
                raise ValueError(
                    "archive_entry sources must include archive_name and "
                    "archive_entry_name"
                )
        else:
            if self.archive_entry_name is not None and self.archive_name is None:
                raise ValueError("archive_entry_name requires archive_name")
        return self

    @property
    def display_name(self) -> str:
        if self.archive_entry_name:
            if self.archive_name:
                return f"{self.archive_name}:{self.archive_entry_name}"
            return self.archive_entry_name
        if self.name:
            return self.name
        if self.path:
            return Path(self.path).name
        return "input"
