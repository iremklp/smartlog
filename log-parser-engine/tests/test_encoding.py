from __future__ import annotations

from pathlib import Path

from log_parser_engine.ingestion import IngestionOptions, decode_text, detect_encoding


def test_detect_encoding_prefers_bom() -> None:
    fixture = Path(__file__).parent / "fixtures" / "ingestion" / "utf8_bom.log"
    detection = detect_encoding(fixture.read_bytes(), options=IngestionOptions())

    assert detection.source == "bom"
    assert detection.encoding == "utf-8-sig"
    assert detection.bom == "utf-8"


def test_decode_text_strips_bom_when_enabled() -> None:
    fixture = Path(__file__).parent / "fixtures" / "ingestion" / "utf8_bom.log"
    options = IngestionOptions()
    detection = detect_encoding(fixture.read_bytes(), options=options)

    decoded = decode_text(fixture.read_bytes(), detection=detection, options=options)

    assert decoded.startswith("Hello UTF-8 BOM")
    assert decoded[0] != "\ufeff"


def test_detect_encoding_uses_explicit_cp1254_fallback() -> None:
    fixture = Path(__file__).parent / "fixtures" / "ingestion" / "windows1254.log"
    options = IngestionOptions(fallback_encodings=("cp1254",))
    detection = detect_encoding(fixture.read_bytes(), options=options)

    assert detection.encoding == "cp1254"
    assert detection.source == "fallback"
