from __future__ import annotations

from datetime import datetime

from log_parser_engine.models import ErrorType, ParseResult, ParseStatus


def sanitize_preview(value: str, *, max_length: int = 200) -> str:
    cleaned = value.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    if len(cleaned) <= max_length:
        return cleaned
    return cleaned[: max_length - 3] + "..."


def extract_error_code(parse_result: ParseResult | None, fallback: str = "PARSE_FAILED") -> str:
    if parse_result is None or not parse_result.errors:
        return fallback
    error_type = parse_result.errors[0].error_type
    if isinstance(error_type, ErrorType):
        return error_type.value.upper()
    return str(error_type).strip().upper() or fallback


def extract_error_message(parse_result: ParseResult | None, *, include_details: bool) -> str:
    if parse_result is None or not parse_result.errors:
        return "parse failed"
    message = parse_result.errors[0].message.strip()
    if not include_details:
        return "parse failed"
    return message or "parse failed"


def parse_result_succeeded(parse_result: ParseResult | None) -> bool:
    return bool(parse_result is not None and parse_result.status == ParseStatus.success)


def update_min_max_timestamps(
    current_min: datetime | None,
    current_max: datetime | None,
    timestamp: datetime,
) -> tuple[datetime | None, datetime | None]:
    minimum = timestamp if current_min is None or timestamp < current_min else current_min
    maximum = timestamp if current_max is None or timestamp > current_max else current_max
    return minimum, maximum
