from __future__ import annotations

from pathlib import Path

import pytest

from log_parser_engine.batch import BatchParseOptions, BatchParseOrchestrator
from log_parser_engine.core import ParserManager, ParserRegistry
from log_parser_engine.exceptions.batch import BatchSourceError
from tests.test_batch_orchestrator import PrefixParser


def _orchestrator() -> BatchParseOrchestrator:
    registry = ParserRegistry([PrefixParser("alpha", "A:")])
    manager = ParserManager(registry)
    return BatchParseOrchestrator(manager)


def test_iter_parse_path_plain_text(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.log"
    file_path.write_text("A: one\nA: two\n", encoding="utf-8")

    stream = _orchestrator().iter_parse_path(file_path)
    results = list(stream)

    assert len(results) == 2
    assert stream.statistics.records_succeeded == 2


def test_iter_parse_path_rejects_zip_suffix(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.zip"
    file_path.write_text("A: one\n", encoding="utf-8")

    with pytest.raises(BatchSourceError):
        _orchestrator().iter_parse_path(file_path)


def test_iter_parse_path_handles_oversized_line(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.log"
    file_path.write_text("AAAAAA\nA: two\n", encoding="utf-8")

    stream = _orchestrator().iter_parse_path(
        file_path,
        options=BatchParseOptions(max_record_characters=3),
    )
    results = list(stream)

    assert any(
        item.status == "failure" and item.error_code == "RECORD_TOO_LARGE"
        for item in results
    )
