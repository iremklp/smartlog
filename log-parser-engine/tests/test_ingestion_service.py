from __future__ import annotations

from pathlib import Path

import pytest

from log_parser_engine.exceptions import (
    ArchiveError,
    BinaryContentError,
    EncryptedArchiveError,
    NestedArchiveError,
)
from log_parser_engine.ingestion import FileIngestionService, IngestionOptions


def _fixture(name: str) -> Path:
    return Path(__file__).parent / "fixtures" / "ingestion" / name


def test_ingest_path_preserves_utf8_bom_when_requested() -> None:
    service = FileIngestionService()
    result = service.ingest_path(
        _fixture("utf8_bom.log"),
        options=IngestionOptions(preserve_original_bytes=True),
    )

    assert result.text.startswith("Hello UTF-8 BOM")
    assert result.original_bytes is not None
    assert result.original_bytes.startswith(b"\xef\xbb\xbf")
    assert result.metadata.encoding.source == "bom"


def test_ingest_path_handles_utf16_text() -> None:
    service = FileIngestionService()
    result = service.ingest_path(_fixture("utf16le.log"))

    assert "Hello UTF-16 LE" in result.text
    assert result.metadata.encoding.bom == "utf-16-le"


def test_ingest_path_handles_fallback_encoding() -> None:
    service = FileIngestionService()
    result = service.ingest_path(
        _fixture("windows1254.log"),
        options=IngestionOptions(fallback_encodings=("cp1254",)),
    )

    assert "İstanbul" in result.text
    assert result.metadata.encoding.encoding == "cp1254"


def test_ingest_path_tracks_mixed_line_endings() -> None:
    service = FileIngestionService()
    result = service.ingest_path(_fixture("mixed_newlines.log"))

    assert result.metadata.line_ending == "mixed"
    assert result.metadata.line_count == 4


def test_ingest_bytes_rejects_binary_content() -> None:
    service = FileIngestionService()

    with pytest.raises(BinaryContentError):
        service.ingest_bytes(_fixture("binary.bin").read_bytes())


def test_ingest_bytes_allows_binary_when_enabled() -> None:
    service = FileIngestionService()
    result = service.ingest_bytes(
        _fixture("binary.bin").read_bytes(),
        options=IngestionOptions(allow_binary=True, fallback_encodings=("latin1",)),
    )

    assert result.metadata.is_binary_like is True
    assert result.text


def test_ingest_bytes_handles_gzip_and_zip_containers() -> None:
    service = FileIngestionService()
    gzip_result = service.ingest_path(_fixture("standard.log.gz"))
    zip_result = service.ingest_path(_fixture("single_file.zip"))

    assert gzip_result.metadata.archive_type == "gzip"
    assert zip_result.metadata.archive_type == "zip"
    assert zip_result.metadata.selected_archive_entry is not None


def test_ingest_bytes_rejects_nested_and_encrypted_archives() -> None:
    service = FileIngestionService()

    with pytest.raises(NestedArchiveError):
        service.ingest_path(
            _fixture("nested_archive.zip"),
            options=IngestionOptions(zip_entry_name="inner.zip"),
        )

    with pytest.raises(EncryptedArchiveError):
        service.ingest_path(_fixture("encrypted.zip"))


def test_ingest_bytes_rejects_malformed_zip() -> None:
    service = FileIngestionService()

    with pytest.raises(ArchiveError):
        service.ingest_path(_fixture("malformed.zip"))


def test_ingest_text_exposes_context_metadata() -> None:
    service = FileIngestionService()
    result = service.ingest_text("hello\nworld\n", source_name="sample.log")

    assert result.original_bytes is None
    assert result.parser_context_attributes["filename"] == "sample.log"
    assert result.parser_context_attributes["extension"] == "log"
    assert result.parser_context_attributes["content_type"] == "text/plain"
