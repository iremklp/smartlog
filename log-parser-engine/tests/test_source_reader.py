from __future__ import annotations

import os
from pathlib import Path

import pytest

from log_parser_engine.exceptions import InputNotFoundError, SymlinkNotAllowedError
from log_parser_engine.ingestion import IngestionOptions, build_source_from_bytes, read_path_bytes


def test_read_path_bytes_reads_regular_file(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.log"
    file_path.write_text("hello\n", encoding="utf-8")

    data, source = read_path_bytes(file_path, options=IngestionOptions())

    assert data == b"hello\n"
    assert source.name == "sample.log"
    assert source.extension == "log"
    assert source.content_type == "text/plain"


def test_read_path_bytes_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(InputNotFoundError):
        read_path_bytes(tmp_path / "missing.log", options=IngestionOptions())


def test_read_path_bytes_rejects_directory(tmp_path: Path) -> None:
    with pytest.raises(Exception):
        read_path_bytes(tmp_path, options=IngestionOptions())


def test_read_path_bytes_rejects_symlink_by_default(tmp_path: Path) -> None:
    target = tmp_path / "target.log"
    target.write_text("hello\n", encoding="utf-8")
    link = tmp_path / "link.log"
    os.symlink(target, link)

    with pytest.raises(SymlinkNotAllowedError):
        read_path_bytes(link, options=IngestionOptions())


def test_read_path_bytes_follows_symlink_when_enabled(tmp_path: Path) -> None:
    target = tmp_path / "target.log"
    target.write_text("hello\n", encoding="utf-8")
    link = tmp_path / "link.log"
    os.symlink(target, link)

    data, source = read_path_bytes(link, options=IngestionOptions(follow_symlinks=True))

    assert data == b"hello\n"
    assert source.name == "link.log"


def test_build_source_from_bytes_uses_source_name() -> None:
    source = build_source_from_bytes(b"abc", source_name="nested/sample.log")

    assert source.kind == "bytes"
    assert source.name == "sample.log"
    assert source.extension == "log"
