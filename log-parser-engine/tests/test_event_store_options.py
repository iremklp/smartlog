
import pytest
from pydantic import ValidationError

from log_parser_engine.storage.options import (
    BatchWriteOptions,
    EventStoreOptions,
    EventWriteOptions,
)


def test_event_store_options_defaults():
    """Tests that default values are set correctly."""
    options = EventStoreOptions()
    assert options.max_events == 100_000
    assert options.max_estimated_memory_bytes == 256 * 1024 * 1024
    assert options.retention_seconds is None
    assert options.eviction_policy == "oldest_inserted"
    assert options.duplicate_policy == "ignore"
    assert options.identity_mode == "existing_or_generated"
    assert options.default_page_size == 100
    assert options.max_page_size == 1_000
    assert options.strict is True


def test_event_store_options_validation():
    """Tests various validation rules for EventStoreOptions."""
    # Test valid configuration
    EventStoreOptions(max_events=1, retention_seconds=1, default_page_size=50, max_page_size=100, max_query_limit=100)

    with pytest.raises(ValidationError):
        EventStoreOptions(max_events=0)  # Must be >= 1

    with pytest.raises(ValidationError):
        EventStoreOptions(max_estimated_memory_bytes=100)  # Must be >= 1 MiB

    with pytest.raises(ValidationError):
        EventStoreOptions(retention_seconds=0)  # Must be >= 1

    with pytest.raises(ValidationError):
        EventStoreOptions(default_page_size=101, max_page_size=100)

    with pytest.raises(ValidationError):
        EventStoreOptions(max_query_limit=99, max_page_size=100)

    with pytest.raises(ValidationError):
        EventStoreOptions(eviction_policy="invalid_policy")

    with pytest.raises(ValidationError, match="Unknown indexed_fields in strict mode: unknown"):
        EventStoreOptions(indexed_fields=("host", "unknown"), strict=True)
    
    # Non-strict mode should allow unknown fields
    EventStoreOptions(indexed_fields=("host", "unknown"), strict=False)


def test_indexed_fields_normalization():
    """Tests that indexed_fields are normalized correctly."""
    options = EventStoreOptions(indexed_fields=("tags", "host", "tags"))
    assert options.indexed_fields == ("host", "tags")


def test_event_write_options_defaults_and_validation():
    """Tests EventWriteOptions."""
    options = EventWriteOptions()
    assert options.event_id is None
    assert options.deduplicate is None
    assert options.duplicate_policy is None
    assert options.apply_retention_before_write is True
    assert options.metadata == {}

    # Test validation
    options = EventWriteOptions(event_id="  ", source_batch_id=" ")
    assert options.event_id is None
    assert options.source_batch_id is None

    with pytest.raises(ValidationError):
        EventWriteOptions(duplicate_policy="invalid")


def test_batch_write_options_defaults():
    """Tests BatchWriteOptions."""
    options = BatchWriteOptions()
    assert options.atomic is True
    assert options.stop_on_error is True
    assert options.max_events is None
