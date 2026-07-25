from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Literal
from urllib.parse import urlsplit

from log_parser_engine.models.enums import LogSeverity, LogSourceType
from log_parser_engine.models.log_event import LogEvent
from log_parser_engine.models.stored_event import StoredEvent

from .helpers import bounded_preview, normalized_text
from .validation import CANONICAL_FIELDS, resolve_attribute_path, resolve_event_field

NumericUnit = Literal["ms", "seconds", "microseconds"]

# Values above this bound are finite Python floats, but their squared deltas can
# overflow streaming variance accumulators. The limit remains far above any
# meaningful duration while leaving ample headroom for bounded accumulation.
_MAX_SAFE_ANALYSIS_MAGNITUDE = 1e100


@dataclass(frozen=True, slots=True)
class NumericFieldSpec:
    """A numeric field path and its explicit unit."""

    path: str
    unit: NumericUnit = "ms"


@dataclass(frozen=True, slots=True)
class ExtractedNumericValue:
    """Outcome of a safe numeric extraction attempt."""

    value: float | None
    field: str | None
    found: bool
    valid: bool
    reason: str | None = None


DEFAULT_DURATION_FIELD_SPECS: tuple[NumericFieldSpec, ...] = (
    NumericFieldSpec("duration_ms"),
    NumericFieldSpec("latency_ms"),
    NumericFieldSpec("response_time_ms"),
    NumericFieldSpec("elapsed_ms"),
    NumericFieldSpec("request_time_ms"),
    NumericFieldSpec("request_time", "seconds"),
    NumericFieldSpec("time_taken_ms"),
    NumericFieldSpec("iis.time_taken_ms"),
    NumericFieldSpec("duration_us", "microseconds"),
    NumericFieldSpec("latency_us", "microseconds"),
)
DEFAULT_DURATION_FIELD_PATHS = tuple(
    field_spec.path for field_spec in DEFAULT_DURATION_FIELD_SPECS
)
_DURATION_UNIT_BY_LEAF = {
    field_spec.path.rsplit(".", 1)[-1]: field_spec.unit
    for field_spec in DEFAULT_DURATION_FIELD_SPECS
}

HTTP_SOURCE_TYPES = frozenset(
    {
        LogSourceType.HTTP,
        LogSourceType.IIS,
        LogSourceType.APACHE,
        LogSourceType.NGINX,
    }
)


def _log_event(event: LogEvent | StoredEvent) -> LogEvent:
    return event.event if isinstance(event, StoredEvent) else event


def _convert_number(value: object, *, strict: bool) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        try:
            converted = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        return converted if math.isfinite(converted) else None
    if not strict and isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        try:
            converted = float(Decimal(cleaned))
        except (InvalidOperation, ValueError, OverflowError):
            return None
        return converted if math.isfinite(converted) else None
    return None


def _unit_multiplier(unit: NumericUnit) -> float:
    if unit == "seconds":
        return 1_000.0
    if unit == "microseconds":
        return 0.001
    return 1.0


def _specs_from_candidates(
    candidates: tuple[str, ...] | list[str],
) -> tuple[NumericFieldSpec, ...]:
    default_units = {spec.path: spec.unit for spec in DEFAULT_DURATION_FIELD_SPECS}
    return tuple(
        NumericFieldSpec(
            path=candidate,
            unit=default_units.get(
                candidate,
                _DURATION_UNIT_BY_LEAF.get(
                    candidate.rsplit(".", 1)[-1],
                    "ms",
                ),
            ),
        )
        for candidate in candidates
    )


def extract_numeric_value(
    event: LogEvent,
    *,
    explicit_field: str | None,
    candidates: tuple[str, ...] | list[str],
    max_depth: int,
    strict: bool = True,
    reject_negative: bool = True,
    field_specs: tuple[NumericFieldSpec, ...] | None = None,
) -> ExtractedNumericValue:
    """Extract the first present numeric field using deterministic precedence."""
    specs = field_specs or _specs_from_candidates(candidates)
    unit_by_path = {spec.path: spec.unit for spec in specs}
    ordered_paths: list[str] = []
    if explicit_field is not None:
        ordered_paths.append(explicit_field)
    ordered_paths.extend(spec.path for spec in specs if spec.path != explicit_field)

    found_invalid: tuple[str, str] | None = None
    for path in ordered_paths:
        raw_values: list[object] = []
        if path in CANONICAL_FIELDS:
            canonical_value = getattr(event, path)
            if canonical_value is not None:
                raw_values.append(canonical_value)
            attribute_found, attribute_value = resolve_attribute_path(
                event.attributes,
                path,
                max_depth=max_depth,
            )
            if attribute_found and attribute_value is not None:
                raw_values.append(attribute_value)
        else:
            found, raw_value = resolve_attribute_path(
                event.attributes,
                path,
                max_depth=max_depth,
            )
            if found and raw_value is not None:
                raw_values.append(raw_value)
        for raw_value in raw_values:
            value = _convert_number(raw_value, strict=strict)
            if value is None:
                if found_invalid is None:
                    found_invalid = (path, "not_numeric_or_non_finite")
                continue
            unit = unit_by_path.get(
                path,
                _DURATION_UNIT_BY_LEAF.get(path.rsplit(".", 1)[-1], "ms"),
            )
            value *= _unit_multiplier(unit)
            if (
                not math.isfinite(value)
                or abs(value) > _MAX_SAFE_ANALYSIS_MAGNITUDE
            ):
                if found_invalid is None:
                    found_invalid = (path, "unit_conversion_overflow")
                continue
            if reject_negative and value < 0:
                if found_invalid is None:
                    found_invalid = (path, "negative_value")
                continue
            return ExtractedNumericValue(
                value=value,
                field=path,
                found=True,
                valid=True,
            )
    if found_invalid is not None:
        return ExtractedNumericValue(
            value=None,
            field=found_invalid[0],
            found=True,
            valid=False,
            reason=found_invalid[1],
        )
    return ExtractedNumericValue(
        value=None,
        field=None,
        found=False,
        valid=False,
        reason="missing",
    )


def extract_duration_ms(
    event: LogEvent | StoredEvent,
    *,
    explicit_field: str | None = None,
    candidates: tuple[str, ...] | list[str] = DEFAULT_DURATION_FIELD_PATHS,
    max_depth: int = 10,
    strict: bool = True,
) -> ExtractedNumericValue:
    """Extract a non-negative duration and normalize it to milliseconds."""
    return extract_numeric_value(
        _log_event(event),
        explicit_field=explicit_field,
        candidates=candidates,
        max_depth=max_depth,
        strict=strict,
        reject_negative=True,
        field_specs=_specs_from_candidates(candidates),
    )


def get_event_timestamp(event: LogEvent | StoredEvent) -> datetime:
    return _log_event(event).timestamp


def get_inserted_at(event: StoredEvent) -> datetime:
    return event.inserted_at


def get_severity(event: LogEvent | StoredEvent) -> LogSeverity:
    severity = _log_event(event).severity
    if isinstance(severity, LogSeverity):
        return severity
    normalized = normalized_text(severity)
    lookup = {
        "trace": LogSeverity.TRACE,
        "debug": LogSeverity.DEBUG,
        "info": LogSeverity.INFO,
        "information": LogSeverity.INFO,
        "notice": LogSeverity.NOTICE,
        "warn": LogSeverity.WARNING,
        "warning": LogSeverity.WARNING,
        "error": LogSeverity.ERROR,
        "fatal": LogSeverity.FATAL,
        "critical": LogSeverity.CRITICAL,
    }
    return lookup.get((normalized or "").casefold(), LogSeverity.UNKNOWN)


def get_event_type(event: LogEvent | StoredEvent) -> str | None:
    log_event = _log_event(event)
    direct = normalized_text(log_event.event_type)
    if direct is not None:
        return direct
    found, value = resolve_attribute_path(log_event.attributes, "event_type")
    return normalized_text(value) if found else None


def get_source_type(event: LogEvent | StoredEvent) -> LogSourceType:
    return _log_event(event).source_type


def get_parser_name(event: LogEvent | StoredEvent) -> str | None:
    log_event = _log_event(event)
    for path in ("parser_name", "parser.name", "parser"):
        found, value = resolve_event_field(log_event, path)
        if found:
            normalized = normalized_text(value)
            if normalized is not None:
                return normalized
    return None


def get_service(event: LogEvent | StoredEvent) -> str | None:
    log_event = _log_event(event)
    direct = normalized_text(log_event.service)
    if direct is not None:
        return direct
    found, value = resolve_attribute_path(log_event.attributes, "service")
    return normalized_text(value) if found else None


def get_host(event: LogEvent | StoredEvent) -> str | None:
    log_event = _log_event(event)
    direct = normalized_text(log_event.host)
    if direct is not None:
        return direct
    found, value = resolve_attribute_path(log_event.attributes, "host")
    return normalized_text(value) if found else None


def get_tags(event: LogEvent | StoredEvent) -> tuple[str, ...]:
    return tuple(
        tag
        for tag in (normalized_text(value) for value in _log_event(event).tags)
        if tag is not None
    )


def get_duration_ms(
    event: LogEvent | StoredEvent,
    *,
    explicit_field: str | None = None,
    candidates: tuple[str, ...] | list[str] = DEFAULT_DURATION_FIELD_PATHS,
    max_depth: int = 10,
    strict: bool = True,
) -> float | None:
    return extract_duration_ms(
        event,
        explicit_field=explicit_field,
        candidates=candidates,
        max_depth=max_depth,
        strict=strict,
    ).value


def _first_field(
    event: LogEvent | StoredEvent,
    *,
    explicit_field: str | None,
    candidates: tuple[str, ...] | list[str],
    max_depth: int = 10,
) -> tuple[str | None, object | None]:
    log_event = _log_event(event)
    ordered = ([explicit_field] if explicit_field is not None else []) + [
        candidate for candidate in candidates if candidate != explicit_field
    ]
    for path in ordered:
        found, value = resolve_event_field(log_event, path, max_depth=max_depth)
        if found and value is not None:
            return path, value
        if path in CANONICAL_FIELDS:
            attribute_found, attribute_value = resolve_attribute_path(
                log_event.attributes,
                path,
                max_depth=max_depth,
            )
            if attribute_found and attribute_value is not None:
                return path, attribute_value
    return None, None


def get_http_status(
    event: LogEvent | StoredEvent,
    *,
    explicit_field: str | None = None,
    candidates: tuple[str, ...] | list[str] = (
        "http_status",
        "status_code",
        "http.status_code",
        "status",
        "sc_status",
    ),
    max_depth: int = 10,
) -> int | None:
    _, value = _first_field(
        event,
        explicit_field=explicit_field,
        candidates=candidates,
        max_depth=max_depth,
    )
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        status = value
    elif isinstance(value, str) and len(value.strip()) == 3 and value.strip().isdigit():
        status = int(value.strip())
    else:
        return None
    return status if 100 <= status <= 599 else None


def get_http_method(
    event: LogEvent | StoredEvent,
    *,
    explicit_field: str | None = None,
    candidates: tuple[str, ...] | list[str] = (
        "http_method",
        "method",
        "http.method",
        "cs_method",
    ),
    max_depth: int = 10,
) -> str | None:
    _, value = _first_field(
        event,
        explicit_field=explicit_field,
        candidates=candidates,
        max_depth=max_depth,
    )
    normalized = normalized_text(value)
    return normalized.upper() if normalized is not None else None


def get_route_template(
    event: LogEvent | StoredEvent,
    *,
    max_depth: int = 10,
) -> str | None:
    log_event = _log_event(event)
    for path in ("route_template", "http.route"):
        found, value = resolve_event_field(log_event, path, max_depth=max_depth)
        if found:
            normalized = normalized_text(value)
            if normalized is not None:
                return normalize_endpoint(normalized)
    return None


def normalize_endpoint(
    value: str,
    *,
    normalize_trailing_slash: bool = True,
) -> str | None:
    """Normalize a URL/path without decoding or guessing dynamic route segments."""
    cleaned = value.strip()
    if not cleaned:
        return None
    parsed = urlsplit(cleaned)
    if parsed.scheme or parsed.netloc:
        path = parsed.path
    else:
        path = cleaned.split("#", 1)[0].split("?", 1)[0]
    if not path:
        path = "/"
    if not path.startswith("/"):
        path = f"/{path}"
    if normalize_trailing_slash and len(path) > 1:
        path = path.rstrip("/")
    return path or "/"


def get_http_path(
    event: LogEvent | StoredEvent,
    *,
    explicit_field: str | None = None,
    candidates: tuple[str, ...] | list[str] = (
        "http_path",
        "path",
        "url.path",
        "request_path",
        "uri",
        "cs_uri_stem",
    ),
    max_depth: int = 10,
    normalize_trailing_slash: bool = True,
) -> str | None:
    route = get_route_template(event, max_depth=max_depth)
    if route is not None and explicit_field is None:
        return route
    _, value = _first_field(
        event,
        explicit_field=explicit_field,
        candidates=candidates,
        max_depth=max_depth,
    )
    normalized = normalized_text(value)
    if normalized is None:
        return None
    return normalize_endpoint(
        normalized,
        normalize_trailing_slash=normalize_trailing_slash,
    )


def get_message_preview(
    event: LogEvent | StoredEvent,
    *,
    limit: int = 200,
) -> str:
    return bounded_preview(_log_event(event).message, limit=limit) or ""


def is_http_event(
    event: LogEvent | StoredEvent,
    *,
    status_field: str | None = None,
    method_field: str | None = None,
    path_field: str | None = None,
    status_candidates: tuple[str, ...] | list[str] = (
        "http_status",
        "status_code",
        "http.status_code",
        "status",
        "sc_status",
    ),
    method_candidates: tuple[str, ...] | list[str] = (
        "http_method",
        "method",
        "http.method",
        "cs_method",
    ),
    path_candidates: tuple[str, ...] | list[str] = (
        "http_path",
        "path",
        "url.path",
        "request_path",
        "uri",
        "cs_uri_stem",
    ),
) -> bool:
    if get_source_type(event) in HTTP_SOURCE_TYPES:
        return True
    return any(
        (
            get_http_status(
                event,
                explicit_field=status_field,
                candidates=status_candidates,
            )
            is not None,
            get_http_method(
                event,
                explicit_field=method_field,
                candidates=method_candidates,
            )
            is not None,
            get_http_path(
                event,
                explicit_field=path_field,
                candidates=path_candidates,
            )
            is not None,
        )
    )


def http_status_class(status: int | None) -> str:
    if status is None or not 100 <= status <= 599:
        return "unknown"
    return f"{status // 100}xx"
