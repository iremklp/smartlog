from __future__ import annotations

import re
from datetime import datetime
from typing import Final

from log_parser_engine.exceptions import RedisTimestampError, RedisTokenizationError
from log_parser_engine.models import RedisLogRecord

from .constants import LEVEL_MARKER_SEVERITY, ROLE_CODES
from .timestamp import parse_outer_timestamp, parse_redis_timestamp

_PREFIX_RE: Final = re.compile(
    r"^(?P<date>[A-Za-z]{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?|\S+)\s+"
    r"(?P<host>\S+)\s+(?P<process>\S+):\s+"
)
_ISO_PREFIX_RE: Final = re.compile(r"^(?P<date>\S+)\s+(?P<stream>stdout|stderr|F|P)\s+")
_LINE_RE: Final = re.compile(
    r"^(?:(?P<pid>\d+):(?P<role>[A-Za-z?])\s+)?(?:\[(?P<bracket_pid>\d+)\]\s+)?"
    r"(?P<day>\d{1,2})\s+(?P<month>[A-Za-z]{3})\s+(?:(?P<year>\d{4})\s+)?"
    r"(?P<time>\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?)\s+"
    r"(?P<marker>[.\-*#])\s+(?P<message>.+)$"
)


def parse_redis_log_line(
    line: str,
    *,
    default_timezone: str = "UTC",
    reference_datetime: datetime | None = None,
    line_number: int | None = None,
) -> RedisLogRecord:
    if not isinstance(line, str) or not line.strip():
        raise RedisTokenizationError("line must not be empty")

    cleaned = line.strip()
    outer_timestamp: datetime | None = None
    outer_host: str | None = None
    outer_process: str | None = None
    attributes: dict[str, object] = {}

    remainder = cleaned
    prefix_match = _PREFIX_RE.match(remainder)
    if prefix_match:
        outer_host = prefix_match.group("host")
        outer_process = prefix_match.group("process")
        try:
            outer_timestamp = parse_outer_timestamp(
                prefix_match.group("date"),
                default_timezone=default_timezone,
                reference_datetime=reference_datetime,
            )
        except RedisTimestampError:
            outer_timestamp = None
        remainder = remainder[prefix_match.end() :]
        attributes["outer_host"] = outer_host
        attributes["outer_process"] = outer_process

    iso_match = _ISO_PREFIX_RE.match(remainder)
    if iso_match and outer_timestamp is None:
        outer_process = iso_match.group("stream")
        try:
            outer_timestamp = parse_outer_timestamp(
                iso_match.group("date"),
                default_timezone=default_timezone,
                reference_datetime=reference_datetime,
            )
        except RedisTimestampError:
            outer_timestamp = None
        remainder = remainder[iso_match.end() :]
        attributes["outer_process"] = outer_process

    match = _LINE_RE.match(remainder)
    if not match:
        raise RedisTokenizationError("redis log line is malformed")

    pid = None
    role_code = None
    role = None
    if match.group("pid") is not None:
        pid = int(match.group("pid"))
        role_code = match.group("role").upper()
        role = ROLE_CODES.get(role_code, None)
        if role is None:
            role = "unknown"
        attributes["pid"] = pid
        attributes["role_code"] = role_code
    elif match.group("bracket_pid") is not None:
        pid = int(match.group("bracket_pid"))
        attributes["pid"] = pid

    year = match.group("year")
    date_text = (
        f"{match.group('day')} {match.group('month')} {year} {match.group('time')}"
        if year is not None
        else f"{match.group('day')} {match.group('month')} {match.group('time')}"
    )
    try:
        timestamp = parse_redis_timestamp(
            date_text,
            default_timezone=default_timezone,
            reference_datetime=reference_datetime,
        )
    except RedisTimestampError as exc:
        raise RedisTokenizationError("invalid redis timestamp") from exc

    marker = match.group("marker")
    if marker not in LEVEL_MARKER_SEVERITY:
        raise RedisTokenizationError("invalid redis level marker")

    message = match.group("message").strip()
    if not message:
        raise RedisTokenizationError("message must not be empty")

    return RedisLogRecord(
        timestamp=timestamp,
        pid=pid,
        role_code=role_code,
        role=role,
        level_marker=marker,
        message=message,
        raw_line=cleaned,
        outer_timestamp=outer_timestamp,
        outer_host=outer_host,
        outer_process=outer_process,
        line_number=line_number,
        attributes=attributes,
        timestamp_source="redis",
    )
