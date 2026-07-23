from __future__ import annotations

from typing import Any

from log_parser_engine.models import LogSeverity, WindowsEventRecord


def map_windows_event_record_to_normalization_fields(
    record: WindowsEventRecord,
) -> dict[str, Any]:
    severity = _map_level_to_severity(record.level)
    event_type = f"windows.event.{record.event_id}"
    message = record.message
    tags = ["windows-event"]
    if record.channel:
        tags.append(record.channel.lower())
    if record.provider_name:
        tags.append(record.provider_name.lower())

    return {
        "timestamp": record.timestamp,
        "severity": severity,
        "source_type": "windows_event",
        "event_type": event_type,
        "message": message,
        "host": record.computer,
        "source": record.channel or record.provider_name,
        "service": record.provider_name,
        "application": record.provider_name,
        "tags": tags,
    }


def _map_level_to_severity(level: int | None) -> LogSeverity:
    mapping = {
        1: LogSeverity.critical,
        2: LogSeverity.error,
        3: LogSeverity.warning,
        4: LogSeverity.info,
        5: LogSeverity.debug,
    }
    if level is None:
        return LogSeverity.UNKNOWN
    return mapping.get(level, LogSeverity.UNKNOWN)
