from __future__ import annotations

import pytest
from pydantic import ValidationError

from log_parser_engine.ingestion import IngestionOptions


def test_ingestion_options_defaults() -> None:
    options = IngestionOptions()

    assert options.max_input_bytes == 50 * 1024 * 1024
    assert options.max_decompressed_bytes == 100 * 1024 * 1024
    assert options.max_compression_ratio == 100.0
    assert options.max_zip_entries == 100
    assert options.allow_gzip is True
    assert options.allow_zip is True
    assert options.allow_binary is False
    assert options.strip_bom is True
    assert options.preserve_original_bytes is False


def test_ingestion_options_normalizes_fallbacks() -> None:
    options = IngestionOptions(
        fallback_encodings=("UTF-8", "cp1254", "utf-8", "iso-8859-1"),
    )

    assert options.effective_fallback_encodings == ("utf-8", "cp1254", "iso-8859-1")


def test_ingestion_options_rejects_invalid_encoding_errors() -> None:
    with pytest.raises(ValidationError):
        IngestionOptions(encoding_errors="boom")


def test_ingestion_options_validates_encoding_name() -> None:
    with pytest.raises(ValidationError):
        IngestionOptions(encoding="not-a-real-codec")
