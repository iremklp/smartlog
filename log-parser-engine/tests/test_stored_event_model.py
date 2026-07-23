
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from log_parser_engine.models import LogEvent, LogSeverity, LogSourceType, StoredEvent


@pytest.fixture
def sample_log_event() -> LogEvent:
    return LogEvent(
        timestamp=datetime.now(timezone.utc),
        source_type=LogSourceType.FILE,
        message="Test message",
        raw_message="Raw test message",
    )


def test_stored_event_creation(sample_log_event: LogEvent):
    """Tests basic creation and property forwarding."""
    now = datetime.now(timezone.utc)
    event = StoredEvent(
        id="evt_123",
        event=sample_log_event,
        inserted_at=now,
        sequence=1,
        content_hash="a" * 64,
        estimated_size_bytes=100,
    )
    assert event.id == "evt_123"
    assert event.event == sample_log_event
    assert event.sequence == 1
    assert event.timestamp == sample_log_event.timestamp
    assert event.severity == sample_log_event.severity
    assert event.event_type == sample_log_event.event_type
    assert event.model_config["frozen"] is True


def test_stored_event_validation(sample_log_event: LogEvent):
    """Tests the validators for the StoredEvent model."""
    now = datetime.now(timezone.utc)

    with pytest.raises(ValidationError, match="id must not be empty"):
        StoredEvent(id=" ", event=sample_log_event, inserted_at=now, sequence=1, content_hash="a"*64, estimated_size_bytes=100)

    with pytest.raises(ValidationError, match="must be an aware UTC datetime"):
        StoredEvent(id="1", event=sample_log_event, inserted_at=datetime.now(), sequence=1, content_hash="a"*64, estimated_size_bytes=100)

    with pytest.raises(ValidationError, match="sequence must be greater than or equal to 1"):
        StoredEvent(id="1", event=sample_log_event, inserted_at=now, sequence=0, content_hash="a"*64, estimated_size_bytes=100)

    with pytest.raises(ValidationError, match="content_hash must be a 64-character"):
        StoredEvent(id="1", event=sample_log_event, inserted_at=now, sequence=1, content_hash="short", estimated_size_bytes=100)

    with pytest.raises(ValidationError, match="estimated_size_bytes must not be negative"):
        StoredEvent(id="1", event=sample_log_event, inserted_at=now, sequence=1, content_hash="a"*64, estimated_size_bytes=-1)

def test_stored_event_metadata_copy(sample_log_event: LogEvent):
    """Ensures that the metadata dictionary is defensively copied."""
    metadata = {"key": "value"}
    event = StoredEvent(
        id="1",
        event=sample_log_event,
        inserted_at=datetime.now(timezone.utc),
        sequence=1,
        content_hash="a" * 64,
        estimated_size_bytes=100,
        metadata=metadata,
    )
    assert event.metadata == metadata
    
    # Modify original metadata dict
    metadata["key"] = "changed"
    
    # The event's metadata should not have changed
    assert event.metadata == {"key": "value"}
