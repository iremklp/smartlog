from __future__ import annotations

from log_parser_engine.models import (
    EncodingDetection,
    IngestionMetadata,
    IngestionResult,
    IngestionSource,
)


def test_ingestion_result_exposes_parser_context_attributes() -> None:
    source = IngestionSource(
        kind="path",
        name="sample.log",
        path="/tmp/sample.log",
        extension="log",
        content_type="text/plain",
        size_bytes=12,
    )
    encoding = EncodingDetection(encoding="utf-8", confidence=1.0, source="text")
    metadata = IngestionMetadata(
        source=source,
        encoding=encoding,
        raw_size_bytes=12,
        decoded_character_count=12,
        line_count=1,
        line_ending="lf",
        has_trailing_newline=False,
        is_binary_like=False,
        null_byte_count=0,
        control_character_count=0,
        sha256="1" * 64,
    )
    result = IngestionResult(text="hello world\n", metadata=metadata)

    attributes = result.parser_context_attributes

    assert attributes["source_name"] == "sample.log"
    assert attributes["filename"] == "sample.log"
    assert attributes["encoding"] == "utf-8"
    assert attributes["sha256"] == "1" * 64


def test_ingestion_result_empty_property_tracks_text() -> None:
    source = IngestionSource(kind="text", name="sample.log", size_bytes=0)
    encoding = EncodingDetection(encoding="utf-8", confidence=1.0, source="text")
    metadata = IngestionMetadata(
        source=source,
        encoding=encoding,
        raw_size_bytes=0,
        decoded_character_count=0,
        line_count=0,
        line_ending="none",
        has_trailing_newline=False,
        is_binary_like=False,
        null_byte_count=0,
        control_character_count=0,
    )
    result = IngestionResult(text="", metadata=metadata)

    assert result.empty is True
