from __future__ import annotations

import re
from datetime import datetime, timezone, tzinfo
from zoneinfo import ZoneInfo

from log_parser_engine.exceptions import (
    SyslogStructureError,
    SyslogTimestampError,
    SyslogTokenizationError,
)
from log_parser_engine.models import SyslogRecord

PRI_PATTERN = re.compile(r"^<(?P<pri>\d{1,3})>(?P<rest>.+)$")
RFC5424_VERSION_PATTERN = re.compile(r"^<(?P<pri>\d{1,3})>1\s")
RFC3164_TIMESTAMP_PATTERN = re.compile(
    r"^(?P<month>[A-Z][a-z]{2})\s+(?P<day>\d{1,2})\s+(?P<time>\d{2}:\d{2}:\d{2})\s+(?P<rest>.+)$"
)


def parse_syslog_message(
    raw_message: str,
    *,
    default_timezone: str = "UTC",
    reference_datetime: datetime | None = None,
    line_number: int | None = None,
) -> SyslogRecord:
    if not isinstance(raw_message, str) or not raw_message.strip():
        raise SyslogTokenizationError("empty syslog message")

    text = raw_message.strip()
    if RFC5424_VERSION_PATTERN.match(text):
        return _parse_rfc5424(text, line_number=line_number)
    return _parse_rfc3164(
        text,
        default_timezone=default_timezone,
        reference_datetime=reference_datetime,
        line_number=line_number,
    )


def _parse_rfc5424(raw_message: str, *, line_number: int | None) -> SyslogRecord:
    match = PRI_PATTERN.match(raw_message)
    if match is None:
        raise SyslogTokenizationError("missing syslog priority")

    priority = int(match.group("pri"))
    rest = match.group("rest")
    version_text, remainder = rest.split(" ", 1)
    if version_text != "1":
        raise SyslogStructureError("invalid RFC 5424 version")
    header_parts = remainder.split(" ", 5)
    if len(header_parts) < 6:
        raise SyslogStructureError("invalid RFC 5424 header")

    timestamp_text, host, application, process_id, message_id, remainder = header_parts
    structured_data, message = _split_structured_data_and_message(remainder)
    timestamp = _parse_iso_timestamp(timestamp_text)
    facility, severity_code = divmod(priority, 8)

    return SyslogRecord(
        raw_message=raw_message,
        priority=priority,
        facility=facility,
        severity_code=severity_code,
        version=1,
        timestamp=timestamp,
        host=None if host == "-" else host,
        application=None if application == "-" else application,
        process_id=None if process_id == "-" else process_id,
        message_id=None if message_id == "-" else message_id,
        structured_data=None if structured_data == "-" else structured_data,
        message=message,
        line_number=line_number,
        attributes={"format": "rfc5424"},
        raw_header=(
            f"<{priority}>{timestamp_text} {host} {application} {process_id} "
            f"{message_id}"
        ),
        timestamp_source="rfc5424",
    )


def _parse_rfc3164(
    raw_message: str,
    *,
    default_timezone: str,
    reference_datetime: datetime | None,
    line_number: int | None,
) -> SyslogRecord:
    match = PRI_PATTERN.match(raw_message)
    if match is None:
        raise SyslogTokenizationError("missing syslog priority")

    priority = int(match.group("pri"))
    remainder = match.group("rest")
    ts_match = RFC3164_TIMESTAMP_PATTERN.match(remainder)
    if ts_match is None:
        raise SyslogStructureError("invalid RFC 3164 header")

    timestamp = _parse_rfc3164_timestamp(
        ts_match.group("month"),
        ts_match.group("day"),
        ts_match.group("time"),
        default_timezone=default_timezone,
        reference_datetime=reference_datetime,
    )
    rest = ts_match.group("rest")

    host, application, message = _parse_rfc3164_body(rest)
    facility, severity_code = divmod(priority, 8)

    return SyslogRecord(
        raw_message=raw_message,
        priority=priority,
        facility=facility,
        severity_code=severity_code,
        version=None,
        timestamp=timestamp,
        host=host,
        application=application,
        process_id=_extract_process_id(application),
        message_id=None,
        structured_data=None,
        message=message,
        line_number=line_number,
        attributes={"format": "rfc3164"},
        raw_header=rest[: len(rest) - len(message)].rstrip(),
        timestamp_source="rfc3164",
    )


def _split_structured_data_and_message(text: str) -> tuple[str, str]:
    cleaned = text.lstrip()
    if cleaned == "-":
        return "-", ""
    if not cleaned.startswith("["):
        raise SyslogStructureError("invalid RFC 5424 structured data")

    index = 0
    length = len(cleaned)
    while index < length and cleaned[index] == "[":
        index = _consume_structured_data_element(cleaned, index)
    structured_data = cleaned[:index]
    message = cleaned[index:].lstrip()
    return structured_data, message


def _consume_structured_data_element(text: str, start: int) -> int:
    index = start + 1
    in_quotes = False
    escape = False
    while index < len(text):
        char = text[index]
        if escape:
            escape = False
        elif char == "\\" and in_quotes:
            escape = True
        elif char == '"':
            in_quotes = not in_quotes
        elif char == "]" and not in_quotes:
            index += 1
            break
        index += 1
    else:
        raise SyslogStructureError("unterminated structured data")

    return index


def _parse_iso_timestamp(value: str) -> datetime:
    cleaned = value.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    try:
        timestamp = datetime.fromisoformat(cleaned)
    except ValueError as exc:
        raise SyslogTimestampError("invalid RFC 5424 timestamp") from exc
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def _parse_rfc3164_timestamp(
    month: str,
    day: str,
    time_text: str,
    *,
    default_timezone: str,
    reference_datetime: datetime | None,
) -> datetime:
    base = reference_datetime or datetime.now(timezone.utc)
    try:
        parsed_tzinfo: tzinfo = ZoneInfo(default_timezone)
    except Exception:  # noqa: BLE001
        parsed_tzinfo = timezone.utc
    try:
        timestamp = datetime.strptime(
            f"{month} {day} {base.year} {time_text}",
            "%b %d %Y %H:%M:%S",
        ).replace(tzinfo=parsed_tzinfo)
    except ValueError as exc:
        raise SyslogTimestampError("invalid RFC 3164 timestamp") from exc
    return timestamp.astimezone(timezone.utc)


def _parse_rfc3164_body(text: str) -> tuple[str | None, str | None, str]:
    cleaned = text.strip()
    host_tag_match = re.match(
        r"^(?P<host>\S+)\s+(?P<tag>[^:]+):\s*(?P<message>.*)$",
        cleaned,
    )
    if host_tag_match is not None:
        host = host_tag_match.group("host")
        tag = host_tag_match.group("tag")
        message = host_tag_match.group("message")
        return host, tag, message

    tag_match = re.match(r"^(?P<tag>[^:]+):\s*(?P<message>.*)$", cleaned)
    if tag_match is not None:
        tag = tag_match.group("tag")
        message = tag_match.group("message")
        return None, tag, message

    raise SyslogStructureError("invalid RFC 3164 message body")


def _extract_process_id(application: str | None) -> str | None:
    if application is None:
        return None
    match = re.match(r"^[^\[]+\[(?P<pid>\d+)\]$", application)
    if match is None:
        return None
    return match.group("pid")
