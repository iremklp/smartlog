
from datetime import datetime, timezone
from uuid import UUID

import pytest

from log_parser_engine.models import LogEvent, LogSourceType
from log_parser_engine.storage.helpers import (
    estimate_event_size_bytes,
    get_canonical_json_bytes,
    resolve_attribute_path,
)
from log_parser_engine.storage.identity import (
    compute_event_content_hash,
    generate_event_id,
)


def test_compute_event_content_hash():
    """Tests that the content hash is deterministic."""
    event1 = LogEvent(
        timestamp=datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        source_type=LogSourceType.FILE,
        message="message",
        raw_message="raw",
        tags=["b", "a"],
        attributes={"key2": "val2", "key1": "val1"},
    )
    event2 = LogEvent(
        timestamp=datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        source_type=LogSourceType.FILE,
        message="message",
        raw_message="different raw", # Should not affect hash
        tags=["a", "b"], # Order should not matter
        attributes={"key1": "val1", "key2": "val2"}, # Order should not matter
    )
    event3 = LogEvent(
        timestamp=datetime(
            2023,
            1,
            1,
            12,
            0,
            1,
            tzinfo=timezone.utc,
        ),
        source_type=LogSourceType.FILE,
        message="message",
        raw_message="raw",
        tags=["a", "b"],
        attributes={"key1": "val1", "key2": "val2"},
    )

    hash1 = compute_event_content_hash(event1)
    hash2 = compute_event_content_hash(event2)
    hash3 = compute_event_content_hash(event3)

    assert isinstance(hash1, str)
    assert len(hash1) == 64
    assert hash1 == hash2
    assert hash1 != hash3

def test_generate_event_id():
    """Tests the different event ID generation modes."""
    event = LogEvent(
        timestamp=datetime.now(timezone.utc),
        source_type=LogSourceType.FILE,
        message="m",
        raw_message="r",
    )

    # existing_or_generated
    event_with_id = LogEvent(
        event_id=UUID("12345678-1234-5678-1234-567812345678"),
        timestamp=datetime.now(timezone.utc),
        source_type=LogSourceType.FILE,
        message="m",
        raw_message="r",
    )
    id1, _ = generate_event_id(
        event_with_id,
        mode="existing_or_generated",
        existing_id=str(event_with_id.event_id),
    )
    assert id1 == f"evt_{event_with_id.event_id}"

    # generated
    id2, _ = generate_event_id(event, mode="generated")
    assert id2.startswith("evt_")
    assert len(id2) == 32 + 4

    # content_hash
    id3, hash3 = generate_event_id(event, mode="content_hash")
    assert id3 == f"evt_{hash3[:32]}"

def test_estimate_event_size():
    """Tests the event size estimation."""
    event = LogEvent(
        timestamp=datetime.now(timezone.utc),
        source_type=LogSourceType.FILE,
        message="a",
        raw_message="b",
    )
    canonical_bytes = get_canonical_json_bytes(event)
    size = estimate_event_size_bytes(canonical_bytes)
    assert size > len(canonical_bytes)
    assert size == len(canonical_bytes) + 256

def test_resolve_attribute_path():
    """Tests the attribute path resolver."""
    event = LogEvent(
        timestamp=datetime.now(timezone.utc),
        source_type=LogSourceType.FILE,
        message="m",
        raw_message="r",
        attributes={
            "http": {"status": 200, "method": "GET"},
            "user": {"id": "abc", "details": {"name": "Test"}},
            "flat": None,
        }
    )
    
    found, val = resolve_attribute_path(event, "http.status")
    assert found and val == 200
    
    found, val = resolve_attribute_path(event, "user.details.name")
    assert found and val == "Test"

    found, val = resolve_attribute_path(event, "flat")
    assert found and val is None

    # Negative cases
    found, val = resolve_attribute_path(event, "http.invalid")
    assert not found and val is None
    
    found, val = resolve_attribute_path(event, "user.details.name.invalid")
    assert not found and val is None
    
    found, val = resolve_attribute_path(event, "invalid.path")
    assert not found and val is None

    # Security cases
    found, val = resolve_attribute_path(event, "__class__")
    assert not found
    found, val = resolve_attribute_path(event, "user..id")
    assert not found


def test_canonical_serialization_rejects_arbitrary_objects() -> None:
    """Content identity must not depend on an object's runtime repr."""

    event = LogEvent(
        timestamp=datetime.now(timezone.utc),
        source_type=LogSourceType.FILE,
        message="message",
        raw_message="message",
        attributes={"unsafe": object()},
    )

    with pytest.raises(TypeError, match="not JSON serializable"):
        get_canonical_json_bytes(event)
