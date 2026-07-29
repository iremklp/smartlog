from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from log_parser_engine.models import LogEvent

STORED_EVENT_METADATA_OVERHEAD_BYTES = 256


def _canonical_json_serializer(value: object) -> object:
    """Serialize only deterministic, JSON-compatible extension values."""

    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (set, frozenset)):
        return sorted(value, key=_canonical_collection_sort_key)
    raise TypeError(
        f"Object of type {type(value).__name__} is not JSON serializable"
    )


def _canonical_collection_sort_key(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=_canonical_json_serializer,
    )


def get_hashable_data(event: LogEvent) -> dict[str, Any]:
    """Return the explicit canonical fields used for content identity."""

    return {
        "timestamp": event.timestamp,
        "severity": event.severity.value,
        "source_type": event.source_type.value,
        "event_type": event.event_type,
        "message": event.message,
        "parser_name": event.attributes.get("parser_name"),
        "parser_version": event.attributes.get("parser_version"),
        "host": event.host,
        "service": event.service,
        "client_ip": event.client_ip,
        "user_id": event.user_id,
        "correlation_id": event.correlation_id,
        "tags": tuple(sorted(event.tags)),
        "attributes": event.attributes,
    }


def get_canonical_json_bytes(
    event: LogEvent,
    for_hashing: bool = False,
) -> bytes:
    """Serialize canonical event identity/size data to deterministic UTF-8."""

    data_to_serialize = get_hashable_data(event)
    if not for_hashing:
        data_to_serialize["raw_message"] = event.raw_message

    canonical_json = json.dumps(
        data_to_serialize,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=_canonical_json_serializer,
    )
    return canonical_json.encode("utf-8")


def estimate_event_size_bytes(canonical_json_bytes: bytes) -> int:
    """Estimate logical store size from serialized bytes plus fixed overhead."""

    return (
        len(canonical_json_bytes)
        + STORED_EVENT_METADATA_OVERHEAD_BYTES
    )


def resolve_attribute_path(
    event: LogEvent,
    path: str,
) -> tuple[bool, object | None]:
    """Resolve a safe dot path only through the event attributes mapping."""

    if (
        not path
        or len(path) > 256
        or path.startswith(".")
        or path.endswith(".")
        or ".." in path
    ):
        return False, None

    segments = path.split(".")
    if len(segments) > 10:
        return False, None

    current: object = event.attributes
    for segment in segments:
        if not segment or segment.startswith("__"):
            return False, None
        if not isinstance(current, Mapping) or segment not in current:
            return False, None
        current = current[segment]
    return True, current
