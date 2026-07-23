from __future__ import annotations

from typing import Any

from log_parser_engine.models import LogSeverity, SyslogRecord


def map_syslog_record_to_normalization_fields(
    record: SyslogRecord, *, flavor: str
) -> dict[str, Any]:
    tags = ["syslog", flavor]
    if record.application:
        tags.append(record.application.lower())
    if record.host:
        tags.append(record.host.lower())

    event_type = None
    if record.message_id and record.message_id != "-":
        event_type = f"syslog.{record.message_id.lower()}"
    elif record.application:
        event_type = f"syslog.{record.application.lower()}"

    return {
        "timestamp": record.timestamp,
        "severity": _map_severity_code(record.severity_code),
        "source_type": "syslog",
        "event_type": event_type,
        "message": record.message,
        "host": record.host,
        "source": record.application,
        "service": record.application,
        "application": record.application,
        "tags": tags,
    }


def _map_severity_code(severity_code: int) -> LogSeverity:
    mapping = {
        0: LogSeverity.fatal,
        1: LogSeverity.fatal,
        2: LogSeverity.critical,
        3: LogSeverity.error,
        4: LogSeverity.warning,
        5: LogSeverity.notice,
        6: LogSeverity.info,
        7: LogSeverity.debug,
    }
    return mapping.get(severity_code, LogSeverity.UNKNOWN)
