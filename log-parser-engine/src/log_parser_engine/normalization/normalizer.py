from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from log_parser_engine.core.parser_context import ParserContext
from log_parser_engine.exceptions import NormalizationError
from log_parser_engine.models import (
    LogEvent,
    LogSeverity,
    LogSourceType,
    NormalizationInput,
    NormalizationResult,
    NormalizationWarning,
)


class Normalizer:
    """Normalize heterogeneous parser payloads into a LogEvent."""

    def __init__(self, field_mapping: dict[str, str] | None = None) -> None:
        self.field_mapping = field_mapping or {}

    def normalize(
        self,
        data: dict[str, Any] | NormalizationInput,
        context: ParserContext | None = None,
    ) -> NormalizationResult:
        if isinstance(data, NormalizationInput):
            payload = data
        else:
            payload = NormalizationInput(data=data)
        mapped = self._apply_mapping(payload.data)
        warnings: list[NormalizationWarning] = []

        timestamp_value = self._extract_value(mapped, "timestamp")
        timestamp = (
            normalize_timestamp(timestamp_value)
            if timestamp_value is not None
            else None
        )
        if timestamp is None:
            raise NormalizationError("timestamp is required")

        severity_value = self._extract_value(mapped, "severity")
        severity = (
            normalize_severity(severity_value)
            if severity_value is not None
            else LogSeverity.UNKNOWN
        )

        duration_value = self._extract_value(mapped, "duration_ms")
        duration_ms = (
            normalize_duration(duration_value)
            if duration_value is not None
            else None
        )

        source_value = self._extract_value(mapped, "source_type")
        source_type = (
            normalize_source_type(source_value)
            if source_value is not None
            else normalize_source_type(payload.source_type or LogSourceType.APPLICATION)
        )

        message_value = self._extract_value(mapped, "message")
        if message_value is None:
            raise NormalizationError("message is required")
        raw_message = str(message_value).strip()

        event = LogEvent(
            timestamp=timestamp,
            source_type=source_type,
            severity=severity,
            message=raw_message,
            raw_message=raw_message,
            service=context.service if context is not None else None,
            application=context.application if context is not None else None,
            environment=context.environment if context is not None else None,
            host=context.host if context is not None else None,
            attributes={
                **(payload.attributes or {}),
                **(context.attributes if context is not None else {}),
            },
            duration_ms=duration_ms,
        )
        return NormalizationResult(event=event, warnings=warnings)

    def _apply_mapping(self, data: dict[str, Any]) -> dict[str, Any]:
        if not self.field_mapping:
            return data
        mapped: dict[str, Any] = {}
        for field_name, original_key in self.field_mapping.items():
            if original_key in data:
                mapped[field_name] = data[original_key]
        return {**data, **mapped}

    def _extract_value(self, data: dict[str, Any], key: str) -> Any:
        if key in data:
            return data[key]
        return None


def build_field_mapping(fields: dict[str, str]) -> dict[str, str]:
    return dict(fields)


def normalize_timestamp(value: Any) -> datetime:
    if value is None:
        raise NormalizationError("timestamp is required")
    if isinstance(value, datetime):
        normalized = value
    elif isinstance(value, str):
        normalized = _parse_timestamp_string(value)
    else:
        raise NormalizationError("timestamp must be a datetime or string")

    if normalized.tzinfo is None:
        normalized = normalized.replace(tzinfo=timezone.utc)
    return normalized.astimezone(timezone.utc)


def normalize_severity(value: Any) -> LogSeverity:
    if value is None:
        return LogSeverity.UNKNOWN
    if isinstance(value, LogSeverity):
        return value
    if isinstance(value, str):
        cleaned = value.strip().lower()
        mapping = {
            "trace": LogSeverity.trace,
            "debug": LogSeverity.debug,
            "info": LogSeverity.info,
            "notice": LogSeverity.notice,
            "warning": LogSeverity.warning,
            "warn": LogSeverity.warning,
            "error": LogSeverity.error,
            "critical": LogSeverity.critical,
            "fatal": LogSeverity.fatal,
            "unknown": LogSeverity.unknown,
        }
        if cleaned in mapping:
            return mapping[cleaned]
    raise NormalizationError("unsupported severity")


def normalize_duration(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        return float(cleaned)
    raise NormalizationError("duration must be numeric")


def normalize_source_type(value: Any) -> LogSourceType:
    if value is None:
        return LogSourceType.UNKNOWN
    if isinstance(value, LogSourceType):
        return value
    if isinstance(value, str):
        cleaned = value.strip().lower()
        normalized = {
            "iis": LogSourceType.iis,
            "redis": LogSourceType.redis,
            "json": LogSourceType.json,
            "xml": LogSourceType.xml,
            "csv": LogSourceType.csv,
            "nginx": LogSourceType.nginx,
            "apache": LogSourceType.apache,
            "windows_event": LogSourceType.windows_event,
            "linux_syslog": LogSourceType.linux_syslog,
            "kubernetes": LogSourceType.kubernetes,
            "openshift": LogSourceType.openshift,
            "jenkins": LogSourceType.jenkins,
            "application": LogSourceType.application,
            "unknown": LogSourceType.unknown,
        }
        if cleaned in normalized:
            return normalized[cleaned]
    raise NormalizationError("unsupported source type")


def _parse_timestamp_string(value: str) -> datetime:
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise NormalizationError("invalid timestamp") from exc
