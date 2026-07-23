from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator

from .ingestion_metadata import IngestionMetadata


class IngestionResult(BaseModel):
    """Immutable logical document produced by the ingestion layer."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    metadata: IngestionMetadata
    original_bytes: bytes | None = None

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return value

    @field_validator("original_bytes")
    @classmethod
    def validate_original_bytes(cls, value: bytes | None) -> bytes | None:
        return value

    @property
    def empty(self) -> bool:
        return self.text == ""

    @property
    def parser_context_attributes(self) -> dict[str, object]:
        source = self.metadata.source
        filename = source.name or (Path(source.path).name if source.path else None)
        return {
            "source_name": source.display_name,
            "filename": filename,
            "extension": source.extension,
            "content_type": source.content_type,
            "encoding": self.metadata.encoding.encoding,
            "bom": self.metadata.encoding.bom,
            "sha256": self.metadata.sha256,
            "archive_type": self.metadata.archive_type,
            "archive_entry_name": source.archive_entry_name,
            "raw_size_bytes": self.metadata.raw_size_bytes,
            "line_ending": self.metadata.line_ending,
        }