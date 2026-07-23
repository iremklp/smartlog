from __future__ import annotations

import pytest
from pydantic import ValidationError

from log_parser_engine.models import (
    EncodingDetection,
    IngestionMetadata,
    IngestionSource,
)


def test_ingestion_metadata_counts_lines_like_splitlines() -> None:
    source = IngestionSource(kind="text", name="sample.log", size_bytes=1)
    encoding = EncodingDetection(
        encoding="utf-8",
        confidence=1.0,
        source="text",
        is_ascii=True,
    )
    metadata = IngestionMetadata(
        source=source,
        encoding=encoding,
        raw_size_bytes=1,
        decoded_character_count=1,
        line_count=1,
        line_ending="lf",
        has_trailing_newline=True,
        is_binary_like=False,
        null_byte_count=0,
        control_character_count=0,
        sha256="0" * 64,
        warnings=(),
    )

    assert metadata.line_count == 1
    assert metadata.has_trailing_newline is True
    assert metadata.sha256 == "0" * 64


def test_ingestion_metadata_rejects_invalid_line_ending() -> None:
    source = IngestionSource(kind="text", name="sample.log", size_bytes=1)
    encoding = EncodingDetection(encoding="utf-8", confidence=1.0, source="text")

    with pytest.raises(ValidationError):
        IngestionMetadata(
            source=source,
            encoding=encoding,
            raw_size_bytes=1,
            decoded_character_count=1,
            line_count=1,
            line_ending="weird",
            has_trailing_newline=False,
            is_binary_like=False,
            null_byte_count=0,
            control_character_count=0,
        )
