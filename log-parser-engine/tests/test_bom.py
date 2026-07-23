from __future__ import annotations

from log_parser_engine.ingestion import detect_bom


def test_detect_bom_for_utf8() -> None:
    encoding, bom_name, bom_length = detect_bom(b"\xef\xbb\xbfhello")

    assert encoding == "utf-8-sig"
    assert bom_name == "utf-8"
    assert bom_length == 3


def test_detect_bom_for_utf32_before_utf16() -> None:
    encoding, bom_name, bom_length = detect_bom(b"\xff\xfe\x00\x00h\x00\x00\x00")

    assert encoding == "utf-32-le"
    assert bom_name == "utf-32-le"
    assert bom_length == 4


def test_detect_bom_for_plain_text_returns_none() -> None:
    assert detect_bom(b"hello") == (None, None, 0)
