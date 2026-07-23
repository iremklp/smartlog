from __future__ import annotations

from pathlib import Path

from log_parser_engine.ingestion import assess_binary_content


def test_assess_binary_content_detects_null_bytes() -> None:
    fixture = Path(__file__).parent / "fixtures" / "ingestion" / "null_bytes.bin"
    assessment = assess_binary_content(fixture.read_bytes())

    assert assessment.null_byte_count > 0
    assert assessment.is_binary_like is True


def test_assess_binary_content_detects_known_magic() -> None:
    fixture = Path(__file__).parent / "fixtures" / "ingestion" / "binary.bin"
    assessment = assess_binary_content(fixture.read_bytes())

    assert "known_binary_magic" in assessment.signals
    assert assessment.printable_ratio < 1.0
