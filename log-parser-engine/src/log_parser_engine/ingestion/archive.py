from __future__ import annotations

import gzip
import io
import zipfile
from pathlib import PurePosixPath

from log_parser_engine.exceptions import (
    ArchiveBombError,
    ArchiveEntrySelectionError,
    ArchiveEntryTooLargeError,
    ArchiveError,
    ArchiveNotAllowedError,
    EncryptedArchiveError,
    NestedArchiveError,
)
from log_parser_engine.models import ArchiveEntryInfo, IngestionSource

from .helpers import guess_content_type, split_name_parts
from .options import IngestionOptions

_ARCHIVE_EXTENSIONS = {"zip", "gz"}


def extract_logical_document(
    data: bytes,
    source: IngestionSource,
    *,
    options: IngestionOptions,
) -> tuple[bytes, IngestionSource, str | None, int | None, ArchiveEntryInfo | None]:
    archive_type = _detect_archive_type(data, source)
    if archive_type is None:
        return data, source, None, None, None

    if archive_type == "gzip":
        if not options.allow_gzip:
            raise ArchiveNotAllowedError("gzip archives are disabled")
        return _extract_gzip(data, source, options)

    if archive_type == "zip":
        if not options.allow_zip:
            raise ArchiveNotAllowedError("zip archives are disabled")
        return _extract_zip(data, source, options)

    return data, source, None, None, None


def _detect_archive_type(data: bytes, source: IngestionSource) -> str | None:
    if data.startswith(b"\x1f\x8b"):
        return "gzip"
    if data.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        return "zip"
    if source.extension in _ARCHIVE_EXTENSIONS:
        return source.extension
    return None


def _extract_gzip(
    data: bytes,
    source: IngestionSource,
    options: IngestionOptions,
) -> tuple[bytes, IngestionSource, str, int, ArchiveEntryInfo | None]:
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(data), mode="rb") as handle:
            decompressed = handle.read(options.max_decompressed_bytes + 1)
    except OSError as exc:
        raise ArchiveError("gzip archive is malformed") from exc
    if len(decompressed) > options.max_decompressed_bytes:
        raise ArchiveBombError("gzip decompression exceeds configured limit")

    ratio = _compression_ratio(len(data), len(decompressed))
    if ratio > options.max_compression_ratio:
        raise ArchiveBombError("gzip compression ratio exceeds configured limit")

    if options.reject_nested_archives and _looks_like_archive(decompressed):
        raise NestedArchiveError("nested archive content is not allowed")

    selected_source = IngestionSource(
        kind=source.kind,
        name=source.name,
        path=source.path,
        extension=source.extension,
        content_type=source.content_type,
        archive_name=source.display_name,
        archive_entry_name=None,
        size_bytes=len(decompressed),
        modified_at=source.modified_at,
    )
    return decompressed, selected_source, "gzip", len(data), None


def _extract_zip(
    data: bytes,
    source: IngestionSource,
    options: IngestionOptions,
) -> tuple[bytes, IngestionSource, str, int, ArchiveEntryInfo]:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = [
                info
                for info in archive.infolist()
                if not _is_ignored_zip_entry(info)
            ]
            if not entries:
                raise ArchiveEntrySelectionError(
                    "zip archive contains no selectable entries"
                )
            if len(entries) > options.max_zip_entries:
                raise ArchiveBombError("zip entry count exceeds configured limit")
            if any(not _is_safe_entry_name(info.filename) for info in entries):
                raise ArchiveEntrySelectionError(
                    "zip archive contains unsafe entry names"
                )

            if options.reject_encrypted_archives and any(
                _is_encrypted(info) for info in entries
            ):
                raise EncryptedArchiveError("encrypted zip archives are not allowed")

            selected_info = _select_zip_entry(entries, options)
            payload = archive.read(selected_info)
            if len(payload) > options.max_selected_entry_bytes:
                raise ArchiveEntryTooLargeError(
                    "selected zip entry exceeds configured limit"
                )
            if len(payload) > options.max_decompressed_bytes:
                raise ArchiveBombError(
                    "zip entry exceeds configured decompression limit"
                )

            ratio = _compression_ratio(
                selected_info.compress_size,
                selected_info.file_size,
            )
            if ratio > options.max_compression_ratio:
                raise ArchiveBombError("zip compression ratio exceeds configured limit")

            if options.reject_nested_archives and _looks_like_archive(
                payload,
                selected_info.filename,
            ):
                raise NestedArchiveError("nested archive content is not allowed")

            entry_info = _build_entry_info(selected_info)
            selected_source = IngestionSource(
                kind="archive_entry",
                name=selected_info.filename,
                path=source.path,
                extension=entry_info.extension,
                content_type=entry_info.content_type,
                archive_name=source.display_name,
                archive_entry_name=selected_info.filename,
                size_bytes=len(payload),
                modified_at=None,
            )
            return payload, selected_source, "zip", len(data), entry_info
    except zipfile.BadZipFile as exc:
        raise ArchiveError("zip archive is malformed") from exc


def _select_zip_entry(
    entries: list[zipfile.ZipInfo],
    options: IngestionOptions,
) -> zipfile.ZipInfo:
    if options.zip_entry_name is not None:
        for info in entries:
            if info.filename == options.zip_entry_name:
                return info
        raise ArchiveEntrySelectionError("requested zip entry was not found")

    candidates = entries
    if options.prefer_text_entries:
        text_candidates = [
            info for info in entries if _build_entry_info(info).text_candidate
        ]
        if text_candidates:
            candidates = text_candidates

    candidates = sorted(candidates, key=lambda info: info.filename)
    if not candidates:
        raise ArchiveEntrySelectionError("zip archive contains no selectable entries")
    if len(candidates) > 1:
        if options.strict:
            raise ArchiveEntrySelectionError(
                "zip archive contains multiple selectable entries"
            )
    return candidates[0]


def _is_ignored_zip_entry(info: zipfile.ZipInfo) -> bool:
    return info.is_dir() or info.file_size < 0 or info.compress_size < 0


def _is_encrypted(info: zipfile.ZipInfo) -> bool:
    return bool(info.flag_bits & 0x1)


def _build_entry_info(info: zipfile.ZipInfo) -> ArchiveEntryInfo:
    extension = split_name_parts(info.filename)[1]
    content_type = guess_content_type(info.filename)
    return ArchiveEntryInfo(
        name=info.filename,
        compressed_size=max(info.compress_size, 0),
        uncompressed_size=max(info.file_size, 0),
        compression_ratio=_compression_ratio(info.compress_size, info.file_size),
        is_directory=info.is_dir(),
        is_encrypted=_is_encrypted(info),
        is_archive=bool(extension in _ARCHIVE_EXTENSIONS),
        extension=extension,
        content_type=content_type,
    )


def _compression_ratio(compressed_size: int, uncompressed_size: int) -> float:
    if uncompressed_size <= 0:
        return 0.0
    return uncompressed_size / max(compressed_size, 1)


def _looks_like_archive(data: bytes, filename: str | None = None) -> bool:
    if data.startswith(b"\x1f\x8b") or data.startswith(
        (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
    ):
        return True
    if filename is None:
        return False
    return split_name_parts(filename)[1] in _ARCHIVE_EXTENSIONS


def _is_safe_entry_name(name: str) -> bool:
    cleaned = name.replace("\\", "/").strip()
    if not cleaned:
        return False
    path = PurePosixPath(cleaned)
    if path.is_absolute():
        return False
    return all(part != ".." for part in path.parts)
