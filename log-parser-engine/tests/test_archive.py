from __future__ import annotations

from pathlib import Path
from pathlib import PurePosixPath

import pytest

from log_parser_engine.exceptions import (
    ArchiveError,
    ArchiveEntrySelectionError,
    ArchiveEntryTooLargeError,
    ArchiveNotAllowedError,
    EncryptedArchiveError,
    NestedArchiveError,
)
from log_parser_engine.ingestion import IngestionOptions, extract_logical_document
from log_parser_engine.models import IngestionSource


def _fixture_bytes(name: str) -> bytes:
    return (Path(__file__).parent / "fixtures" / "ingestion" / name).read_bytes()


def _source(name: str) -> IngestionSource:
    extension = PurePosixPath(name).suffix.lstrip(".") or None
    return IngestionSource(
        kind="bytes",
        name=name,
        extension=extension,
        size_bytes=len(_fixture_bytes(name)),
    )


def test_extract_logical_document_handles_gzip() -> None:
    source_name = "standard.log.gz"
    data = _fixture_bytes(source_name)
    logical_bytes, logical_source, archive_type, compressed_size, selected_entry = extract_logical_document(
        data,
        _source(source_name),
        options=IngestionOptions(),
    )

    assert archive_type == "gzip"
    assert compressed_size == len(data)
    assert selected_entry is None
    assert logical_source.archive_name == source_name
    assert b"Hello UTF-8" in logical_bytes


def test_extract_logical_document_selects_single_zip_entry() -> None:
    source_name = "single_file.zip"
    data = _fixture_bytes(source_name)
    logical_bytes, logical_source, archive_type, compressed_size, selected_entry = extract_logical_document(
        data,
        _source(source_name),
        options=IngestionOptions(),
    )

    assert archive_type == "zip"
    assert compressed_size == len(data)
    assert selected_entry is not None
    assert selected_entry.name == "single.log"
    assert logical_source.kind == "archive_entry"
    assert b"Hello UTF-8" in logical_bytes


def test_extract_logical_document_prefers_text_entry() -> None:
    source_name = "multi_file.zip"
    data = _fixture_bytes(source_name)
    _, _, _, _, selected_entry = extract_logical_document(
        data,
        _source(source_name),
        options=IngestionOptions(strict=False),
    )

    assert selected_entry is not None
    assert selected_entry.name == "alpha.log"


def test_extract_logical_document_rejects_nested_archive_selection() -> None:
    source_name = "nested_archive.zip"
    data = _fixture_bytes(source_name)

    with pytest.raises(NestedArchiveError):
        extract_logical_document(
            data,
            _source(source_name),
            options=IngestionOptions(zip_entry_name="inner.zip"),
        )


def test_extract_logical_document_rejects_encrypted_archives() -> None:
    source_name = "encrypted.zip"
    data = _fixture_bytes(source_name)

    with pytest.raises(EncryptedArchiveError):
        extract_logical_document(data, _source(source_name), options=IngestionOptions())


def test_extract_logical_document_rejects_oversized_entries() -> None:
    source_name = "oversized_entry.zip"
    data = _fixture_bytes(source_name)

    with pytest.raises(ArchiveEntryTooLargeError):
        extract_logical_document(
            data,
            _source(source_name),
            options=IngestionOptions(max_selected_entry_bytes=1024),
        )


def test_extract_logical_document_rejects_empty_zip() -> None:
    source_name = "empty.zip"
    data = _fixture_bytes(source_name)

    with pytest.raises(ArchiveEntrySelectionError):
        extract_logical_document(data, _source(source_name), options=IngestionOptions())


def test_extract_logical_document_rejects_malformed_zip() -> None:
    source_name = "malformed.zip"
    data = _fixture_bytes(source_name)

    with pytest.raises(ArchiveError):
        extract_logical_document(data, _source(source_name), options=IngestionOptions())
