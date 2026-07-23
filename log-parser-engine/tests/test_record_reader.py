from __future__ import annotations

from io import StringIO

import pytest

from log_parser_engine.batch.options import BatchParseOptions
from log_parser_engine.batch.record_reader import LineRecordReader, iter_bounded_lines
from log_parser_engine.exceptions.batch import BatchSourceError


def test_line_record_reader_removes_terminal_newline() -> None:
    reader = LineRecordReader()
    items = list(reader.iter_records(["a\n", "b\r\n"], options=BatchParseOptions()))
    assert items[0].raw == "a"
    assert items[1].raw == "b"


def test_line_record_reader_rejects_non_string() -> None:
    reader = LineRecordReader()
    with pytest.raises(BatchSourceError):
        list(reader.iter_records(["a", 1], options=BatchParseOptions()))  # type: ignore[list-item]


def test_iter_bounded_lines_marks_oversized() -> None:
    stream = StringIO("abcdef\nnext\n")
    lines = list(iter_bounded_lines(stream, max_characters=4))
    assert lines[0].oversized is True
    assert lines[1].text == "next"
