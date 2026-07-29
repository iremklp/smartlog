
from __future__ import annotations

import hashlib
from uuid import uuid4

from log_parser_engine.models import LogEvent

from ..exceptions import InvalidEventIdError
from .helpers import get_canonical_json_bytes


def compute_event_content_hash(event: LogEvent) -> str:
    """
    Computes a deterministic SHA-256 hash for the content of a LogEvent.
    """
    canonical_bytes = get_canonical_json_bytes(event, for_hashing=True)
    hasher = hashlib.sha256()
    hasher.update(canonical_bytes)
    return hasher.hexdigest()


def generate_event_id(
    event: LogEvent,
    *,
    mode: str,
    existing_id: str | None = None,
) -> tuple[str, str]:
    """
    Generates a unique event ID and content hash based on the configured mode.

    Args:
        event: The LogEvent.
        mode: The identity mode ('generated', 'content_hash', 'existing_or_generated').
        existing_id: An existing ID from the event, if any.

    Returns:
        A tuple containing (event_id, content_hash).
    """
    content_hash = compute_event_content_hash(event)

    if mode == "existing_or_generated":
        if existing_id:
            event_id = (
                existing_id
                if existing_id.startswith("evt_")
                else f"evt_{existing_id}"
            )
        else:
            event_id = f"evt_{uuid4().hex}"
    elif mode == "generated":
        event_id = f"evt_{uuid4().hex}"
    elif mode == "content_hash":
        event_id = f"evt_{content_hash[:32]}"  # Use a prefix of the hash
    else:
        raise ValueError(f"Unknown identity mode: {mode}")

    if not event_id:
        raise InvalidEventIdError("Generated event ID cannot be empty.")

    return event_id, content_hash
