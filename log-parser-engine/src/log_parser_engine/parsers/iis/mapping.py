from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from log_parser_engine.models import LogSeverity, LogSourceType
from log_parser_engine.models.iis_record import IisW3CRecord

from .constants import NULL_MARKER


def parse_optional_int(value: str | None) -> int | None:
    if value is None or value == NULL_MARKER:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def parse_optional_float(value: str | None) -> float | None:
    if value is None or value == NULL_MARKER:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def severity_from_http_status(status: int | None) -> LogSeverity:
    if status is None:
        return LogSeverity.INFO
    if status >= 500:
        return LogSeverity.ERROR
    if status >= 400:
        return LogSeverity.WARNING
    return LogSeverity.INFO


def build_iis_event_message(
    method: str | None,
    path: str | None,
    status: int | None,
) -> str:
    method_value = (method or "HTTP").strip()
    path_value = (path or "request").strip()
    if status is None:
        return f"{method_value} {path_value}"
    return f"{method_value} {path_value} -> {status}"


def map_iis_record_to_normalization_fields(record: IisW3CRecord) -> dict[str, Any]:
    fields = record.fields
    date_value = fields.get("date")
    time_value = fields.get("time")
    timestamp = None
    if date_value and time_value:
        timestamp = _build_timestamp(date_value, time_value)
    elif date_value:
        timestamp = _coerce_timestamp(date_value)
    elif time_value:
        timestamp = _coerce_timestamp(time_value)

    mapped: dict[str, Any] = {
        "timestamp": timestamp,
        "source_type": LogSourceType.IIS,
        "severity": severity_from_http_status(
            parse_optional_int(fields.get("sc-status"))
        ),
        "message": build_iis_event_message(
            fields.get("cs-method"),
            fields.get("cs-uri-stem"),
            parse_optional_int(fields.get("sc-status")),
        ),
        "raw_message": record.raw_line,
        "service": fields.get("s-sitename"),
        "host": fields.get("s-computername"),
        "client_ip": fields.get("c-ip"),
        "server_ip": fields.get("s-ip"),
        "http_method": fields.get("cs-method"),
        "http_path": fields.get("cs-uri-stem"),
        "http_status": parse_optional_int(fields.get("sc-status")),
        "duration_ms": parse_optional_float(fields.get("time-taken")),
        "user_id": fields.get("cs-username"),
    }

    attributes: dict[str, Any] = {
        "iis": {
            "substatus": parse_optional_int(fields.get("sc-substatus")),
            "win32_status": parse_optional_int(fields.get("sc-win32-status")),
            "server_port": parse_optional_int(fields.get("s-port")),
            "substatus_value": parse_optional_int(fields.get("sc-substatus")),
            "win32_status_value": parse_optional_int(fields.get("sc-win32-status")),
            "query_string": fields.get("cs-uri-query"),
            "user_agent": fields.get("cs(user-agent)"),
            "referer": fields.get("cs(referer)"),
            "cookie": fields.get("cs(cookie)"),
            "request_bytes": parse_optional_int(fields.get("cs-bytes")),
            "response_bytes": parse_optional_int(fields.get("sc-bytes")),
            "http_version": fields.get("cs-version"),
            "protocol": fields.get("cs-protocol"),
            "extra_values": record.extra_values,
            "missing_fields": record.missing_fields,
            "field_order": record.field_order,
        },
        "iis_fields": {
            key: value
            for key, value in fields.items()
            if key not in {"date", "time"}
        },
    }
    mapped["attributes"] = attributes
    return mapped


def _build_timestamp(date_value: str, time_value: str) -> datetime:
    text = f"{date_value}T{time_value}"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return _coerce_timestamp(date_value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _coerce_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        parsed = datetime.fromisoformat(value.replace(" ", "T"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
