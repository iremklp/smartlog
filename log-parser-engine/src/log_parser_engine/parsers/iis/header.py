from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from log_parser_engine.exceptions import IisHeaderError
from log_parser_engine.models import IisW3CHeader

from .constants import DIRECTIVE_PREFIX


def parse_iis_directive(line: str) -> tuple[str, str]:
    cleaned = line.strip()
    if not cleaned.startswith(DIRECTIVE_PREFIX):
        raise IisHeaderError("line is not an IIS directive")
    if ":" not in cleaned:
        raise IisHeaderError("directive must contain a ':' separator")
    key, value = cleaned[1:].split(":", 1)
    key_value = key.strip().lower()
    if not key_value:
        raise IisHeaderError("directive key must not be empty")
    return key_value, value.strip()


def parse_iis_fields(value: str) -> tuple[str, ...]:
    cleaned = value.strip()
    if not cleaned:
        raise IisHeaderError("fields value must not be empty")
    parts = [part.strip().lower() for part in cleaned.split() if part.strip()]
    if not parts:
        raise IisHeaderError("fields value must not be empty")
    seen: set[str] = set()
    normalized: list[str] = []
    for part in parts:
        if part in seen:
            raise IisHeaderError(f"duplicate field '{part}'")
        seen.add(part)
        normalized.append(part)
    return tuple(normalized)


def parse_iis_header(lines: Iterable[str]) -> IisW3CHeader:
    directives: dict[str, str] = {}
    fields: tuple[str, ...] | None = None
    software: str | None = None
    version: str | None = None
    date_value: datetime | None = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if not stripped.startswith(DIRECTIVE_PREFIX):
            continue
        key, value = parse_iis_directive(stripped)
        directives[key] = value
        if key == "software":
            software = value
        elif key == "version":
            version = value
        elif key == "date":
            date_value = _parse_date(value)
        elif key == "fields":
            fields = parse_iis_fields(value)

    if fields is None:
        raise IisHeaderError("#Fields directive is required")

    return IisW3CHeader(
        software=software,
        version=version,
        date=date_value,
        fields=fields,
        directives=directives,
    )


def extract_header_and_data_lines(raw_log: str) -> tuple[IisW3CHeader, tuple[str, ...]]:
    lines = [line.rstrip("\n") for line in raw_log.splitlines()]
    directives: list[str] = []
    data_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(DIRECTIVE_PREFIX):
            directives.append(line)
            continue
        data_lines.append(line)
    header = parse_iis_header(directives)
    return header, tuple(data_lines)


def _parse_date(value: str) -> datetime:
    normalized = value.strip()
    if not normalized:
        raise IisHeaderError("date value must not be empty")
    try:
        if " " in normalized:
            parsed = datetime.fromisoformat(normalized.replace(" ", "T"))
        else:
            parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise IisHeaderError("invalid date value") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
