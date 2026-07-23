from __future__ import annotations

from log_parser_engine.ingestion import analyze_line_endings


def test_line_endings_detect_mixed() -> None:
    analysis = analyze_line_endings("first\r\nsecond\nthird\rfourth")

    assert analysis.line_ending == "mixed"
    assert analysis.line_count == 4
    assert analysis.has_trailing_newline is False


def test_line_endings_follow_splitlines_semantics() -> None:
    assert analyze_line_endings("").line_count == 0
    assert analyze_line_endings("abc\n").line_count == 1
    assert analyze_line_endings("\n").line_count == 1
