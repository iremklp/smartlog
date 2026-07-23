
from __future__ import annotations

from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

# Constants
ONE_MIB = 1024 * 1024

# Allowed values
EVICTION_POLICIES = Literal[
    "oldest_inserted",
    "oldest_event_timestamp",
    "reject_new",
]
DUPLICATE_POLICIES = Literal[
    "reject",
    "ignore",
    "replace",
]
IDENTITY_MODES = Literal[
    "generated",
    "content_hash",
    "existing_or_generated",
]
RETENTION_BASIS_OPTIONS = Literal[
    "inserted_at",
    "event_timestamp",
]
DEFAULT_INDEXED_FIELDS = (
    "severity",
    "source_type",
    "event_type",
    "parser_name",
    "service",
    "host",
    "tags",
)


class EventStoreOptions(BaseModel):
    """Immutable configuration for the in-memory event store."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_events: int = Field(
        default=100_000,
        description="Maximum number of events to store.",
    )
    max_estimated_memory_bytes: int | None = Field(
        default=256 * 1024 * 1024,
        description="Maximum estimated memory usage in bytes for stored events.",
    )
    retention_seconds: int | None = Field(
        default=None,
        description="Automatically remove events older than this value in seconds.",
    )
    retention_basis: RETENTION_BASIS_OPTIONS = Field(
        default="inserted_at",
        description="The timestamp basis for applying retention policy.",
    )
    eviction_policy: EVICTION_POLICIES = Field(
        default="oldest_inserted",
        description="Policy to apply when the store reaches its capacity limits.",
    )
    duplicate_policy: DUPLICATE_POLICIES = Field(
        default="ignore",
        description="Default policy for handling duplicate events.",
    )
    identity_mode: IDENTITY_MODES = Field(
        default="existing_or_generated",
        description="How to determine the unique ID for an event.",
    )
    enable_indexes: bool = Field(
        default=True,
        description="Enable secondary indexes for faster queries on supported fields.",
    )
    indexed_fields: tuple[str, ...] = Field(
        default=DEFAULT_INDEXED_FIELDS,
        description="Fields to create secondary indexes for.",
    )
    max_query_limit: int = Field(
        default=10_000,
        description="Maximum number of events a single query can return.",
    )
    default_page_size: int = Field(
        default=100,
        description="Default number of events per page in query results.",
    )
    max_page_size: int = Field(
        default=1_000,
        description="Maximum number of events per page a user can request.",
    )
    max_batch_events: int = Field(
        default=10_000,
        description="Maximum number of events allowed in a single `add_many` call.",
    )
    snapshot_enabled: bool = Field(
        default=True,
        description="Allow creating snapshots of the event store.",
    )
    max_snapshot_events: int = Field(
        default=100_000,
        description="Maximum number of events to include in a snapshot.",
    )
    max_snapshot_bytes: int = Field(
        default=256 * ONE_MIB,
        description="Maximum estimated size of a snapshot in bytes.",
    )
    strict: bool = Field(
        default=True,
        description="If true, enforce strict validation and raise errors for potential issues.",
    )

    @field_validator("max_events", "max_batch_events")
    @classmethod
    def _validate_positive_integer(cls, value: int) -> int:
        if value < 1:
            raise ValueError("must be greater than or equal to 1")
        return value

    @field_validator("max_estimated_memory_bytes")
    @classmethod
    def _validate_memory_limit(cls, value: int | None) -> int | None:
        if value is not None and value < ONE_MIB:
            raise ValueError(f"must be None or at least {ONE_MIB} bytes (1 MiB)")
        return value

    @field_validator("retention_seconds")
    @classmethod
    def _validate_retention(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError("must be None or greater than or equal to 1")
        return value

    @field_validator("indexed_fields")
    @classmethod
    def _normalize_indexed_fields(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        # This simple normalization ensures no duplicates and a consistent order.
        return tuple(sorted(list(set(value))))

    @model_validator(mode="after")
    def _validate_model(self) -> "EventStoreOptions":
        if self.default_page_size > self.max_page_size:
            raise ValueError("default_page_size cannot be greater than max_page_size")

        if self.max_query_limit < self.max_page_size:
            raise ValueError("max_query_limit cannot be less than max_page_size")

        if self.strict:
            # In strict mode, all indexed_fields must be known default fields
            unknown_fields = set(self.indexed_fields) - set(DEFAULT_INDEXED_FIELDS)
            if unknown_fields:
                raise ValueError(f"Unknown indexed_fields in strict mode: {', '.join(sorted(list(unknown_fields)))}")
        return self


class EventWriteOptions(BaseModel):
    """Immutable options for a single event write operation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str | None = Field(
        default=None,
        description="Explicit event ID to use. Overrides store's identity_mode.",
    )
    deduplicate: bool | None = Field(
        default=None,
        description="Whether to perform content-hash based deduplication for this event.",
    )
    duplicate_policy: DUPLICATE_POLICIES | None = Field(
        default=None,
        description="Override the store's default duplicate policy for this event.",
    )
    apply_retention_before_write: bool = Field(
        default=True,
        description="If true, the retention policy is applied before this write operation.",
    )
    source_batch_id: str | None = Field(
        default=None,
        description="Optional identifier for the source batch this event belongs to.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom metadata to associate with the stored event.",
    )

    @field_validator("event_id", "source_batch_id")
    @classmethod
    def _validate_stripped_string(cls, value: str | None) -> str | None:
        if value is not None:
            stripped = value.strip()
            if not stripped:
                return None
            return stripped
        return None

    @field_validator("metadata")
    @classmethod
    def _defensive_copy_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        return value.copy()


class BatchWriteOptions(BaseModel):
    """Options for a batch `add_many` operation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    atomic: bool = Field(
        default=True,
        description="If true, the entire batch write is all-or-nothing.",
    )
    stop_on_error: bool = Field(
        default=True,
        description="In non-atomic mode, stop processing the batch on the first error.",
    )
    max_events: int | None = Field(
        default=None,
        description="Override the store's max_batch_events for this operation.",
    )
