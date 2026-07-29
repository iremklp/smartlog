from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator


class ArchiveEntryInfo(BaseModel):
    """Immutable metadata for a selected archive entry."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    compressed_size: int
    uncompressed_size: int
    compression_ratio: float
    is_directory: bool
    is_encrypted: bool
    is_archive: bool
    extension: str | None = None
    content_type: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("name must not be empty")
        return cleaned

    @field_validator("compressed_size", "uncompressed_size")
    @classmethod
    def validate_sizes(cls, value: int) -> int:
        if value < 0:
            raise ValueError("size must not be negative")
        return value

    @field_validator("compression_ratio")
    @classmethod
    def validate_ratio(cls, value: float) -> float:
        if value < 0:
            raise ValueError("compression_ratio must not be negative")
        return value

    @field_validator("extension")
    @classmethod
    def validate_extension(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        if not cleaned:
            return None
        return cleaned[1:] if cleaned.startswith(".") else cleaned

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        return cleaned or None

    @property
    def text_candidate(self) -> bool:
        if self.is_directory or self.is_encrypted or self.is_archive:
            return False
        if self.content_type is not None and self.content_type.startswith("text/"):
            return True
        if self.content_type in {
            "application/json",
            "application/xml",
            "application/csv",
        }:
            return True
        return self.extension in {
            "log",
            "txt",
            "json",
            "jsonl",
            "ndjson",
            "xml",
            "csv",
            "yaml",
            "yml",
            "ini",
            "cfg",
            "conf",
        }
