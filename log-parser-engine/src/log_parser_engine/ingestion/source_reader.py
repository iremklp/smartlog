from __future__ import annotations

import stat
from datetime import datetime, timezone
from pathlib import Path

from log_parser_engine.exceptions import (
    InputNotFoundError,
    InputPermissionError,
    InputSourceError,
    InputTooLargeError,
    SymlinkNotAllowedError,
)
from log_parser_engine.models import IngestionSource

from .helpers import guess_content_type, split_name_parts
from .options import IngestionOptions


def read_path_bytes(
    path: str | Path,
    *,
    options: IngestionOptions,
) -> tuple[bytes, IngestionSource]:
    source_path = Path(path)
    try:
        st = source_path.lstat()
    except FileNotFoundError as exc:
        raise InputNotFoundError(f"input path not found: {source_path}") from exc
    except PermissionError as exc:
        raise InputPermissionError(f"cannot access input path: {source_path}") from exc

    if stat.S_ISLNK(st.st_mode):
        if not options.follow_symlinks:
            raise SymlinkNotAllowedError(f"symlink not allowed: {source_path}")
        try:
            st = source_path.stat()
        except FileNotFoundError as exc:
            raise InputNotFoundError(f"input path not found: {source_path}") from exc

    if not stat.S_ISREG(st.st_mode):
        raise InputSourceError(f"input path is not a regular file: {source_path}")

    if st.st_size > options.max_input_bytes:
        raise InputTooLargeError(f"input exceeds configured limit: {source_path}")

    try:
        with source_path.open("rb") as handle:
            data = handle.read(options.max_input_bytes + 1)
    except PermissionError as exc:
        raise InputPermissionError(f"cannot read input path: {source_path}") from exc

    if len(data) > options.max_input_bytes:
        raise InputTooLargeError(f"input exceeds configured limit: {source_path}")

    _, extension = split_name_parts(source_path.name)
    modified_at = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)
    source = IngestionSource(
        kind="path",
        name=source_path.name,
        path=str(source_path),
        extension=extension,
        content_type=guess_content_type(source_path.name),
        size_bytes=len(data),
        modified_at=modified_at,
    )
    return data, source


def build_source_from_bytes(
    data: bytes,
    *,
    source_name: str | None,
) -> IngestionSource:
    name, extension = split_name_parts(source_name)
    return IngestionSource(
        kind="bytes",
        name=name,
        path=None,
        extension=extension,
        content_type=guess_content_type(source_name),
        size_bytes=len(data),
        modified_at=None,
    )
