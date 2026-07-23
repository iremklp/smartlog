from __future__ import annotations

import codecs
import mimetypes
from pathlib import Path


def normalize_extension(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip().lower()
    if not cleaned:
        return None
    return cleaned[1:] if cleaned.startswith(".") else cleaned


def normalize_content_type(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip().lower()
    if not cleaned:
        return None
    return cleaned.split(";", 1)[0].strip()


def guess_content_type(name: str | None) -> str | None:
    if not name:
        return None
    return normalize_content_type(mimetypes.guess_type(name)[0])


def split_name_parts(name: str | None) -> tuple[str | None, str | None]:
    if name is None:
        return None, None
    cleaned = name.strip()
    if not cleaned:
        return None, None
    path = Path(cleaned)
    stem = path.name
    extension = normalize_extension(path.suffix)
    return stem, extension


def normalize_codec_name(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip().lower()
    if not cleaned:
        return None
    try:
        codecs.lookup(cleaned)
    except LookupError as exc:
        raise ValueError(f"unknown codec: {value}") from exc
    return cleaned


def dedupe_strings(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = str(value).strip().lower()
        if not cleaned or cleaned in seen:
            continue
        normalized.append(cleaned)
        seen.add(cleaned)
    return tuple(normalized)
