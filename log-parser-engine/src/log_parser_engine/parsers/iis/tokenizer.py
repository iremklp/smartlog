from __future__ import annotations

from log_parser_engine.exceptions import IisTokenizationError

from .constants import NULL_MARKER


def tokenize_iis_line(line: str) -> tuple[str, ...]:
    cleaned = line.strip()
    if not cleaned:
        raise IisTokenizationError("line must not be empty")
    if cleaned.startswith("#"):
        raise IisTokenizationError("directive lines are not data lines")
    return tuple(cleaned.split())


def build_iis_record(
    *,
    fields: tuple[str, ...],
    line: str,
    line_number: int | None = None,
    strict: bool = False,
) -> tuple[dict[str, str | None], tuple[str, ...], tuple[str, ...]]:
    tokens = tokenize_iis_line(line)
    if len(tokens) < len(fields):
        if strict:
            raise IisTokenizationError("not enough tokens for the declared fields")
        missing = fields[len(tokens) :]
        values = dict(zip(fields[: len(tokens)], tokens))
        normalized = {
            key: (None if value == NULL_MARKER else value)
            for key, value in values.items()
        }
        return normalized, tuple(missing), tuple()

    if len(tokens) > len(fields):
        if strict:
            raise IisTokenizationError("too many tokens for the declared fields")
        values = dict(zip(fields, tokens[: len(fields)]))
        normalized = {
            key: (None if value == NULL_MARKER else value)
            for key, value in values.items()
        }
        return normalized, tuple(), tuple(tokens[len(fields) :])

    values = dict(zip(fields, tokens))
    normalized = {
        key: (None if value == NULL_MARKER else value)
        for key, value in values.items()
    }
    return normalized, tuple(), tuple()
