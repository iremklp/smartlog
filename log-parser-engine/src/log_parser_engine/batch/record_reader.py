from __future__ import annotations

import codecs
from dataclasses import dataclass
from io import TextIOBase
from pathlib import Path
from typing import Iterable, Iterator, Protocol

from log_parser_engine.exceptions import InputNotFoundError, SymlinkNotAllowedError
from log_parser_engine.exceptions.batch import BatchSourceError

from .helpers import sanitize_preview
from .options import BatchParseOptions
from .state import ParserRecordStrategy


@dataclass(frozen=True, slots=True)
class SourceRecord:
    index: int
    line_start: int | None
    line_end: int | None
    raw: str | None
    preview: str | None
    character_count: int
    oversized: bool
    kind_hint: str


@dataclass(frozen=True, slots=True)
class BoundedLine:
    text: str | None
    preview: str | None
    line_number: int
    character_count: int
    oversized: bool
    had_newline: bool


class RecordReader(Protocol):
    def iter_records(
        self,
        source: Iterable[str],
        *,
        options: BatchParseOptions,
    ) -> Iterator[SourceRecord]: ...


class LineRecordReader:
    """Yield one logical record per source line."""

    def iter_records(
        self,
        source: Iterable[str],
        *,
        options: BatchParseOptions,
    ) -> Iterator[SourceRecord]:
        line_number = 0
        index = 0
        for line in source:
            line_number += 1
            if not isinstance(line, str):
                raise BatchSourceError("line iterable must yield strings")
            index += 1
            raw = line.rstrip("\r\n")
            char_count = len(raw)
            if char_count > options.max_record_characters:
                yield SourceRecord(
                    index=index,
                    line_start=line_number,
                    line_end=line_number,
                    raw=None,
                    preview=sanitize_preview(raw),
                    character_count=char_count,
                    oversized=True,
                    kind_hint="data",
                )
                continue

            kind_hint = "blank" if raw == "" else "data"
            yield SourceRecord(
                index=index,
                line_start=line_number,
                line_end=line_number,
                raw=raw,
                preview=sanitize_preview(raw) if raw else "",
                character_count=char_count,
                oversized=False,
                kind_hint=kind_hint,
            )


class MultilineDocumentReader:
    """Yield the entire source as one logical record."""

    def iter_records(
        self,
        source: Iterable[str],
        *,
        options: BatchParseOptions,
    ) -> Iterator[SourceRecord]:
        parts: list[str] = []
        line_count = 0
        for line in source:
            line_count += 1
            if not isinstance(line, str):
                raise BatchSourceError("line iterable must yield strings")
            parts.append(line)
        text = "".join(parts)
        if text == "":
            return
        stripped = text.rstrip("\r\n")
        character_count = len(stripped)
        if character_count > options.max_record_characters:
            yield SourceRecord(
                index=1,
                line_start=1 if line_count else None,
                line_end=line_count if line_count else None,
                raw=None,
                preview=sanitize_preview(stripped),
                character_count=character_count,
                oversized=True,
                kind_hint="document",
            )
            return
        yield SourceRecord(
            index=1,
            line_start=1 if line_count else None,
            line_end=line_count if line_count else None,
            raw=stripped,
            preview=sanitize_preview(stripped),
            character_count=character_count,
            oversized=False,
            kind_hint="document",
        )


class AutoRecordReader:
    """Resolve reader implementation based on parser strategy and options."""

    def __init__(self) -> None:
        self._line = LineRecordReader()
        self._document = MultilineDocumentReader()

    def select(
        self,
        *,
        options: BatchParseOptions,
        strategy: ParserRecordStrategy | None,
    ) -> RecordReader:
        if options.record_mode == "line":
            return self._line
        if options.record_mode == "multiline_document":
            return self._document

        if strategy is not None and strategy.mode == "document":
            return self._document
        return self._line


def iter_bounded_lines(
    stream: TextIOBase,
    *,
    max_characters: int,
) -> Iterator[BoundedLine]:
    line_number = 0
    while True:
        chunk = stream.readline(max_characters + 1)
        if chunk == "":
            break

        line_number += 1
        ended_with_newline = chunk.endswith("\n") or chunk.endswith("\r")
        content = chunk.rstrip("\r\n")

        if len(content) <= max_characters and ended_with_newline:
            yield BoundedLine(
                text=content,
                preview=sanitize_preview(content),
                line_number=line_number,
                character_count=len(content),
                oversized=False,
                had_newline=True,
            )
            continue

        if (
            len(content) <= max_characters
            and not ended_with_newline
            and len(chunk) <= max_characters
        ):
            yield BoundedLine(
                text=content,
                preview=sanitize_preview(content),
                line_number=line_number,
                character_count=len(content),
                oversized=False,
                had_newline=False,
            )
            continue

        # Oversized logical line: continue draining until newline or EOF.
        total = len(content)
        preview = content
        while True:
            extra = stream.readline(max_characters + 1)
            if extra == "":
                ended_with_newline = False
                break
            extra_content = extra.rstrip("\r\n")
            total += len(extra_content)
            if len(preview) < 200:
                preview += extra_content
            if extra.endswith("\n") or extra.endswith("\r"):
                ended_with_newline = True
                break

        yield BoundedLine(
            text=None,
            preview=sanitize_preview(preview),
            line_number=line_number,
            character_count=total,
            oversized=True,
            had_newline=ended_with_newline,
        )


def iter_records_from_bounded_lines(
    lines: Iterable[BoundedLine],
) -> Iterator[SourceRecord]:
    index = 0
    for line in lines:
        index += 1
        kind_hint = "blank" if line.text == "" else "data"
        yield SourceRecord(
            index=index,
            line_start=line.line_number,
            line_end=line.line_number,
            raw=line.text,
            preview=line.preview,
            character_count=line.character_count,
            oversized=line.oversized,
            kind_hint=kind_hint if not line.oversized else "data",
        )


def open_text_stream(
    path: str | Path,
    *,
    encoding: str,
    errors: str,
    follow_symlinks: bool,
) -> TextIOBase:
    try:
        codecs.lookup(encoding)
    except LookupError as exc:
        raise BatchSourceError("unknown encoding") from exc

    file_path = Path(path)
    if not file_path.exists():
        raise InputNotFoundError("input path does not exist")
    if file_path.is_symlink() and not follow_symlinks:
        raise SymlinkNotAllowedError("symlink paths are not allowed")
    if not file_path.is_file():
        raise BatchSourceError("input path must be a regular file")
    if file_path.suffix.lower() in {".gz", ".zip"}:
        raise BatchSourceError("iter_parse_path only supports plain text files")

    try:
        return file_path.open("r", encoding=encoding, errors=errors, newline="")
    except OSError as exc:
        raise BatchSourceError("failed to open source path") from exc
