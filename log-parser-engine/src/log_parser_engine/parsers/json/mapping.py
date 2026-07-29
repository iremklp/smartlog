from __future__ import annotations

from copy import deepcopy
from typing import Any

from log_parser_engine.models import JsonFieldMapping, JsonProfileDetection
from log_parser_engine.models.enums import LogSeverity

from .constants import GENERIC_DEFAULT_PATHS, RESERVED_CANONICAL_FIELDS
from .field_path import FieldPathResolver


def map_json_record_to_normalization_fields(
    data: dict[str, object],
    profile: JsonProfileDetection,
    field_mapping: JsonFieldMapping | None = None,
) -> dict[str, Any]:
    mapping = field_mapping or JsonFieldMapping.generic_defaults()
    canonical: dict[str, Any] = {}
    for field_name in _canonical_field_order():
        value = _resolve_field_value(data, mapping, field_name)
        if value is not None:
            canonical[field_name] = value

    canonical.setdefault("timestamp", _coerce_timestamp(data))
    canonical.setdefault("message", _coerce_message(data))
    canonical.setdefault("severity", _coerce_severity(data))
    canonical.setdefault("service", _coerce_service(data))
    canonical.setdefault("application", _coerce_application(data))
    canonical.setdefault("environment", _coerce_environment(data))
    canonical.setdefault("host", _coerce_host(data))
    canonical.setdefault("source", _coerce_source(data))
    canonical.setdefault("event_type", _coerce_event_type(data))
    canonical.setdefault("trace_id", _coerce_trace_id(data))
    canonical.setdefault("correlation_id", _coerce_correlative_id(data))
    canonical.setdefault("user_id", _coerce_user_id(data))
    canonical.setdefault("client_ip", _coerce_client_ip(data))
    canonical.setdefault("server_ip", _coerce_server_ip(data))
    canonical.setdefault("http_method", _coerce_http_method(data))
    canonical.setdefault("http_path", _coerce_http_path(data))
    canonical.setdefault("http_status", _coerce_http_status(data))
    canonical.setdefault("duration_ms", _coerce_duration(data))
    canonical.setdefault("tags", _coerce_tags(data))
    canonical.setdefault("attributes", _coerce_attributes(data))

    return {
        "timestamp": canonical.get("timestamp"),
        "severity": canonical.get("severity"),
        "message": canonical.get("message"),
        "event_type": canonical.get("event_type"),
        "service": canonical.get("service"),
        "application": canonical.get("application"),
        "environment": canonical.get("environment"),
        "host": canonical.get("host"),
        "source": canonical.get("source"),
        "trace_id": canonical.get("trace_id"),
        "correlation_id": canonical.get("correlation_id"),
        "user_id": canonical.get("user_id"),
        "client_ip": canonical.get("client_ip"),
        "server_ip": canonical.get("server_ip"),
        "http_method": canonical.get("http_method"),
        "http_path": canonical.get("http_path"),
        "http_status": canonical.get("http_status"),
        "duration_ms": canonical.get("duration_ms"),
        "tags": canonical.get("tags"),
        "attributes": canonical.get("attributes"),
        "profile": profile.profile,
        "profile_confidence": profile.confidence,
        "raw_data": deepcopy(data),
    }


def _canonical_field_order() -> tuple[str, ...]:
    return tuple(sorted(RESERVED_CANONICAL_FIELDS))


def _resolve_field_value(
    data: dict[str, object],
    mapping: JsonFieldMapping,
    field_name: str,
) -> Any:
    field_attr = f"{field_name}_paths"
    if field_name == "duration_ms":
        field_attr = "duration_ms_paths"
    path_candidates = getattr(mapping, field_attr)
    resolver = FieldPathResolver(path_candidates)
    return resolver.resolve(data)


def _coerce_timestamp(data: dict[str, object]) -> Any:
    for path in GENERIC_DEFAULT_PATHS["timestamp"]:
        value = _resolve_nested(data, path)
        if value is not None:
            return value
    return None


def _coerce_message(data: dict[str, object]) -> Any:
    for path in GENERIC_DEFAULT_PATHS["message"]:
        value = _resolve_nested(data, path)
        if value is not None:
            return value
    return None


def _coerce_severity(data: dict[str, object]) -> Any:
    for path in GENERIC_DEFAULT_PATHS["severity"]:
        value = _resolve_nested(data, path)
        if value is not None:
            if isinstance(value, str):
                normalized = value.strip().lower()
                if normalized in {
                    "info",
                    "warning",
                    "error",
                    "debug",
                    "trace",
                    "fatal",
                    "critical",
                    "notice",
                }:
                    return normalized
                if normalized in {"warn"}:
                    return "warning"
            if isinstance(value, (int, float)):
                return LogSeverity(str(value)).value if False else None
    return None


def _coerce_service(data: dict[str, object]) -> Any:
    for path in GENERIC_DEFAULT_PATHS["service"]:
        value = _resolve_nested(data, path)
        if value is not None:
            return value
    return None


def _coerce_application(data: dict[str, object]) -> Any:
    for path in GENERIC_DEFAULT_PATHS["application"]:
        value = _resolve_nested(data, path)
        if value is not None:
            return value
    return None


def _coerce_environment(data: dict[str, object]) -> Any:
    for path in GENERIC_DEFAULT_PATHS["environment"]:
        value = _resolve_nested(data, path)
        if value is not None:
            return value
    return None


def _coerce_host(data: dict[str, object]) -> Any:
    for path in GENERIC_DEFAULT_PATHS["host"]:
        value = _resolve_nested(data, path)
        if value is not None:
            return value
    return None


def _coerce_source(data: dict[str, object]) -> Any:
    for path in GENERIC_DEFAULT_PATHS["source"]:
        value = _resolve_nested(data, path)
        if value is not None:
            return value
    return None


def _coerce_event_type(data: dict[str, object]) -> Any:
    for path in GENERIC_DEFAULT_PATHS["event_type"]:
        value = _resolve_nested(data, path)
        if value is not None:
            return value
    return None


def _coerce_trace_id(data: dict[str, object]) -> Any:
    for path in GENERIC_DEFAULT_PATHS["trace_id"]:
        value = _resolve_nested(data, path)
        if value is not None:
            return value
    return None


def _coerce_correlative_id(data: dict[str, object]) -> Any:
    for path in GENERIC_DEFAULT_PATHS["correlation_id"]:
        value = _resolve_nested(data, path)
        if value is not None:
            return value
    return None


def _coerce_user_id(data: dict[str, object]) -> Any:
    for path in GENERIC_DEFAULT_PATHS["user_id"]:
        value = _resolve_nested(data, path)
        if value is not None:
            return value
    return None


def _coerce_client_ip(data: dict[str, object]) -> Any:
    for path in GENERIC_DEFAULT_PATHS["client_ip"]:
        value = _resolve_nested(data, path)
        if value is not None:
            return value
    return None


def _coerce_server_ip(data: dict[str, object]) -> Any:
    for path in GENERIC_DEFAULT_PATHS["server_ip"]:
        value = _resolve_nested(data, path)
        if value is not None:
            return value
    return None


def _coerce_http_method(data: dict[str, object]) -> Any:
    for path in GENERIC_DEFAULT_PATHS["http_method"]:
        value = _resolve_nested(data, path)
        if value is not None:
            return value
    return None


def _coerce_http_path(data: dict[str, object]) -> Any:
    for path in GENERIC_DEFAULT_PATHS["http_path"]:
        value = _resolve_nested(data, path)
        if value is not None:
            return value
    return None


def _coerce_http_status(data: dict[str, object]) -> Any:
    for path in GENERIC_DEFAULT_PATHS["http_status"]:
        value = _resolve_nested(data, path)
        if value is not None:
            return value
    return None


def _coerce_duration(data: dict[str, object]) -> Any:
    for path in GENERIC_DEFAULT_PATHS["duration_ms"]:
        value = _resolve_nested(data, path)
        if value is not None:
            return value
    return None


def _coerce_tags(data: dict[str, object]) -> Any:
    for path in GENERIC_DEFAULT_PATHS["tags"]:
        value = _resolve_nested(data, path)
        if value is not None:
            return value
    return None


def _coerce_attributes(data: dict[str, object]) -> Any:
    for path in GENERIC_DEFAULT_PATHS["attributes"]:
        value = _resolve_nested(data, path)
        if value is not None:
            if isinstance(value, dict):
                return dict(value)
            return value
    return {}


def _resolve_nested(data: dict[str, object], path: str) -> Any:
    resolver = FieldPathResolver((path,))
    return resolver.resolve(data)
