from __future__ import annotations

import codecs

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .helpers import dedupe_strings, normalize_codec_name


class IngestionOptions(BaseModel):
    """Immutable options controlling a single ingestion execution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_input_bytes: int = Field(default=50 * 1024 * 1024)
    max_decompressed_bytes: int = Field(default=100 * 1024 * 1024)
    max_compression_ratio: float = Field(default=100.0)
    max_zip_entries: int = Field(default=100)
    max_selected_entry_bytes: int = Field(default=50 * 1024 * 1024)
    allow_gzip: bool = True
    allow_zip: bool = True
    allow_binary: bool = False
    allow_empty: bool = False
    follow_symlinks: bool = False
    encoding: str | None = None
    encoding_errors: str = "strict"
    detect_encoding: bool = True
    encoding_confidence_threshold: float = 0.60
    fallback_encodings: tuple[str, ...] = ("utf-8", "cp1252", "iso-8859-1")
    normalize_newlines: bool = False
    strip_bom: bool = True
    compute_sha256: bool = True
    zip_entry_name: str | None = None
    prefer_text_entries: bool = True
    reject_nested_archives: bool = True
    reject_encrypted_archives: bool = True
    strict: bool = True
    preserve_original_bytes: bool = False

    @field_validator(
        "max_input_bytes",
        "max_decompressed_bytes",
        "max_zip_entries",
        "max_selected_entry_bytes",
    )
    @classmethod
    def validate_limits(cls, value: int) -> int:
        if value < 1:
            raise ValueError("limit must be 1 or greater")
        return value

    @field_validator("max_compression_ratio")
    @classmethod
    def validate_compression_ratio(cls, value: float) -> float:
        if value < 1.0:
            raise ValueError("max_compression_ratio must be 1.0 or greater")
        return value

    @field_validator("encoding_confidence_threshold")
    @classmethod
    def validate_confidence_threshold(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError(
                "encoding_confidence_threshold must be between 0.0 and 1.0"
            )
        return value

    @field_validator("encoding")
    @classmethod
    def validate_encoding(cls, value: str | None) -> str | None:
        cleaned = normalize_codec_name(value)
        return cleaned

    @field_validator("encoding_errors")
    @classmethod
    def validate_encoding_errors(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned not in {"strict", "replace", "ignore"}:
            raise ValueError("encoding_errors must be strict, replace, or ignore")
        return cleaned

    @field_validator("fallback_encodings")
    @classmethod
    def validate_fallback_encodings(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = dedupe_strings(value)
        for encoding in normalized:
            codecs.lookup(encoding)
        return normalized

    @field_validator("zip_entry_name")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def validate_option_relationships(self) -> "IngestionOptions":
        if self.encoding is not None and self.detect_encoding:
            return self
        return self

    @property
    def effective_fallback_encodings(self) -> tuple[str, ...]:
        return self.fallback_encodings
