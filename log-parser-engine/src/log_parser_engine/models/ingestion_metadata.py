from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .archive_entry_info import ArchiveEntryInfo
from .encoding_detection import EncodingDetection
from .ingestion_source import IngestionSource
from .ingestion_warning import IngestionWarning


class IngestionMetadata(BaseModel):
    """Immutable diagnostics describing a single ingestion operation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source: IngestionSource
    encoding: EncodingDetection
    raw_size_bytes: int
    decoded_character_count: int
    line_count: int
    line_ending: str
    has_trailing_newline: bool
    is_binary_like: bool
    null_byte_count: int
    control_character_count: int
    sha256: str | None = None
    archive_type: str | None = None
    compressed_size_bytes: int | None = None
    decompressed_size_bytes: int | None = None
    selected_archive_entry: ArchiveEntryInfo | None = None
    warnings: tuple[IngestionWarning, ...] = ()
    attributes: dict[str, object] = Field(default_factory=dict)

    @field_validator(
        "raw_size_bytes",
        "decoded_character_count",
        "line_count",
        "null_byte_count",
        "control_character_count",
    )
    @classmethod
    def validate_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("value must not be negative")
        return value

    @field_validator("compressed_size_bytes", "decompressed_size_bytes")
    @classmethod
    def validate_optional_sizes(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("size must not be negative")
        return value

    @field_validator("sha256")
    @classmethod
    def normalize_sha256(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        if not cleaned:
            return None
        if len(cleaned) != 64 or any(char not in "0123456789abcdef" for char in cleaned):
            raise ValueError("sha256 must be a lowercase hex digest")
        return cleaned

    @field_validator("line_ending")
    @classmethod
    def validate_line_ending(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned not in {"lf", "crlf", "cr", "mixed", "none"}:
            raise ValueError("invalid line ending")
        return cleaned

    @field_validator("archive_type")
    @classmethod
    def normalize_archive_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        return cleaned or None

    @field_validator("warnings")
    @classmethod
    def normalize_warnings(cls, value: tuple[IngestionWarning, ...]) -> tuple[IngestionWarning, ...]:
        return tuple(value)

    @field_validator("attributes")
    @classmethod
    def normalize_attributes(cls, value: dict[str, object]) -> dict[str, object]:
        return dict(value)