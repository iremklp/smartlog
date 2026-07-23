
from __future__ import annotations

import json
from typing import Any

from log_parser_engine.models import LogEvent

# A rough estimate for the overhead of a StoredEvent object in memory,
# including dictionary overhead, references, etc.
STORED_EVENT_METADATA_OVERHEAD_BYTES = 256


def _canonical_json_serializer(obj: Any) -> Any:
    """Custom JSON serializer for deterministic output."""
    if hasattr(obj, "isoformat"):  # Works for datetime
        return obj.isoformat()
    if hasattr(obj, "value"):  # Works for enums
        return obj.value
    if isinstance(obj, set):  # Handle sets by sorting them
        return sorted(list(obj))
    # Let Pydantic handle UUIDs, etc.
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    if isinstance(obj, (dict, list, tuple)):
         # The default json.dumps recursion will handle these
        return obj
    # For other types, we rely on Pydantic's serialization or raise an error
    try:
        # Fallback to a standard representation
        return str(obj)
    except Exception:
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

def get_hashable_data(event: LogEvent) -> dict[str, Any]:
    """Returns the dictionary of data used for content hashing."""
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

def get_canonical_json_bytes(event: LogEvent, for_hashing: bool = False) -> bytes:
    """
    Serializes a LogEvent to its canonical JSON representation in UTF-8 bytes.
    """
    data_to_serialize = get_hashable_data(event)
    if not for_hashing:
        # raw_message is included for size estimation but not for content hash
        data_to_serialize["raw_message"] = event.raw_message

    # Use pydantic's model_dump_json which is fast and handles types correctly
    canonical_json = json.dumps(
        data_to_serialize,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_canonical_json_serializer,
    )
    return canonical_json.encode("utf-8")


def estimate_event_size_bytes(canonical_json_bytes: bytes) -> int:
    """
    Estimates the memory usage of a `LogEvent` based on its canonical
    JSON representation, plus a fixed overhead for `StoredEvent` metadata.
    """
    return len(canonical_json_bytes) + STORED_EVENT_METADATA_OVERHEAD_BYTES


def resolve_attribute_path(event: LogEvent, path: str) -> tuple[bool, Any | None]:
    """
    Safely resolves a dot-notation path within an event's attributes.

    Returns a tuple of (found, value).
    """
    if not path or path.startswith(".") or path.endswith(".") or ".." in path:
        return False, None

    segments = path.split('.')
    if len(segments) > 10:  # Max depth
        return False, None

    current: Any = event.attributes
    for segment in segments:
        if not segment or segment.startswith("__"):  # Disallow empty and dunder segments
            return False, None

        if isinstance(current, dict):
            if segment not in current:
                return False, None
            current = current.get(segment)
        else:
            # Cannot traverse further
            return False, None

    return True, current
