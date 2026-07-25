from __future__ import annotations

from collections.abc import Mapping, Sequence

from log_parser_engine.models.log_event import LogEvent
from log_parser_engine.models.stored_event import StoredEvent

CANONICAL_FIELDS = frozenset(
    {
        "application",
        "client_ip",
        "correlation_id",
        "duration_ms",
        "environment",
        "event_id",
        "event_type",
        "host",
        "http_method",
        "http_path",
        "http_status",
        "ingested_at",
        "message",
        "raw_message",
        "schema_version",
        "server_ip",
        "service",
        "severity",
        "source",
        "source_type",
        "tags",
        "timestamp",
        "trace_id",
        "user_id",
    }
)


def validate_field_path(path: str, *, max_depth: int = 10) -> str:
    """Validate a safe dot-separated attribute path."""
    cleaned = path.strip()
    if not cleaned or len(cleaned) > 256:
        raise ValueError("field path must contain 1-256 characters")
    parts = cleaned.split(".")
    if len(parts) > max_depth:
        raise ValueError("field path exceeds the maximum depth")
    for part in parts:
        if (
            not part
            or part.startswith("__")
            or not part.replace("_", "").replace("-", "").isalnum()
        ):
            raise ValueError("field path contains an unsafe segment")
    return cleaned


def resolve_attribute_path(
    attributes: Mapping[str, object],
    path: str,
    *,
    max_depth: int = 10,
) -> tuple[bool, object | None]:
    """Resolve a path only through mappings; object attribute access is forbidden."""
    try:
        cleaned = validate_field_path(path, max_depth=max_depth)
    except ValueError:
        return False, None
    current: object = attributes
    for segment in cleaned.split("."):
        if not isinstance(current, Mapping) or segment not in current:
            return False, None
        current = current[segment]
    return True, current


def resolve_event_field(
    event: LogEvent,
    path: str,
    *,
    max_depth: int = 10,
) -> tuple[bool, object | None]:
    """Resolve known canonical fields first and otherwise use safe attributes."""
    try:
        cleaned = validate_field_path(path, max_depth=max_depth)
    except ValueError:
        return False, None
    if cleaned in CANONICAL_FIELDS:
        return True, getattr(event, cleaned)
    return resolve_attribute_path(event.attributes, cleaned, max_depth=max_depth)


def validate_stored_events(events: Sequence[StoredEvent]) -> None:
    """Validate that an analysis snapshot contains only StoredEvent objects."""
    for event in events:
        if not isinstance(event, StoredEvent):
            raise TypeError("events must contain only StoredEvent instances")
