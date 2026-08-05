from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from log_parser_engine.models import (
    BatchParseResult,
    BatchWriteResult,
    EventAggregationResult,
    EventQueryResult,
    EventStoreStatistics,
    EventWriteResult,
    ParseResult,
    ParserRegistration,
    PipelineResult,
    StoredEvent,
)


class ParserMetadataApiResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    display_name: str
    version: str
    source_type: str
    description: str | None
    author: str | None
    homepage: str | None
    supported_extensions: tuple[str, ...]
    supported_content_types: tuple[str, ...]
    priority: int
    enabled_by_default: bool
    supports_multiline: bool
    supports_batch: bool
    thread_safe: bool
    experimental: bool
    tags: tuple[str, ...]


class ParserRegistrationApiResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    parser_name: str
    parser_version: str
    source_type: str
    enabled: bool
    registered_at: datetime
    registration_order: int
    metadata: ParserMetadataApiResponse

    @classmethod
    def from_domain(cls, value: ParserRegistration) -> "ParserRegistrationApiResponse":
        return cls(
            parser_name=value.parser_name,
            parser_version=value.parser_version,
            source_type=value.source_type.value,
            enabled=value.enabled,
            registered_at=value.registered_at,
            registration_order=value.registration_order,
            metadata=ParserMetadataApiResponse(
                name=value.metadata.name,
                display_name=value.metadata.display_name,
                version=value.metadata.version,
                source_type=value.metadata.source_type.value,
                description=value.metadata.description,
                author=value.metadata.author,
                homepage=value.metadata.homepage,
                supported_extensions=tuple(value.metadata.supported_extensions),
                supported_content_types=tuple(value.metadata.supported_content_types),
                priority=value.metadata.priority,
                enabled_by_default=value.metadata.enabled_by_default,
                supports_multiline=value.metadata.supports_multiline,
                supports_batch=value.metadata.supports_batch,
                thread_safe=value.metadata.thread_safe,
                experimental=value.metadata.experimental,
                tags=tuple(value.metadata.tags),
            ),
        )


class EventSummaryApiResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str
    event_id: UUID
    timestamp: datetime
    ingested_at: datetime
    source_type: str
    severity: str
    event_type: str | None
    message: str
    service: str | None
    application: str | None
    environment: str | None
    host: str | None
    source: str | None
    trace_id: str | None
    correlation_id: str | None
    user_id: str | None
    client_ip: str | None
    server_ip: str | None
    http_method: str | None
    http_path: str | None
    http_status: int | None
    duration_ms: float | None
    attributes: dict[str, Any] = Field(default_factory=dict)
    tags: tuple[str, ...] = ()


class EventDetailApiResponse(EventSummaryApiResponse):
    raw_message: str


class StoredEventSummaryApiResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    event: EventSummaryApiResponse
    inserted_at: datetime
    sequence: int
    source_batch_id: str | None

    @classmethod
    def from_domain(cls, value: StoredEvent) -> "StoredEventSummaryApiResponse":
        return cls(
            id=value.id,
            event=EventSummaryApiResponse(
                schema_version=value.event.schema_version,
                event_id=value.event.event_id,
                timestamp=value.event.timestamp,
                ingested_at=value.event.ingested_at,
                source_type=value.event.source_type.value,
                severity=value.event.severity.value,
                event_type=value.event.event_type,
                message=value.event.message,
                service=value.event.service,
                application=value.event.application,
                environment=value.event.environment,
                host=value.event.host,
                source=value.event.source,
                trace_id=value.event.trace_id,
                correlation_id=value.event.correlation_id,
                user_id=value.event.user_id,
                client_ip=value.event.client_ip,
                server_ip=value.event.server_ip,
                http_method=value.event.http_method,
                http_path=value.event.http_path,
                http_status=value.event.http_status,
                duration_ms=value.event.duration_ms,
                attributes=dict(value.event.attributes),
                tags=tuple(value.event.tags),
            ),
            inserted_at=value.inserted_at,
            sequence=value.sequence,
            source_batch_id=value.source_batch_id,
        )


class StoredEventDetailApiResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    event: EventDetailApiResponse
    inserted_at: datetime
    sequence: int
    source_batch_id: str | None

    @classmethod
    def from_domain(cls, value: StoredEvent) -> "StoredEventDetailApiResponse":
        return cls(
            id=value.id,
            event=EventDetailApiResponse(
                schema_version=value.event.schema_version,
                event_id=value.event.event_id,
                timestamp=value.event.timestamp,
                ingested_at=value.event.ingested_at,
                source_type=value.event.source_type.value,
                severity=value.event.severity.value,
                event_type=value.event.event_type,
                message=value.event.message,
                raw_message=value.event.raw_message,
                service=value.event.service,
                application=value.event.application,
                environment=value.event.environment,
                host=value.event.host,
                source=value.event.source,
                trace_id=value.event.trace_id,
                correlation_id=value.event.correlation_id,
                user_id=value.event.user_id,
                client_ip=value.event.client_ip,
                server_ip=value.event.server_ip,
                http_method=value.event.http_method,
                http_path=value.event.http_path,
                http_status=value.event.http_status,
                duration_ms=value.event.duration_ms,
                attributes=dict(value.event.attributes),
                tags=tuple(value.event.tags),
            ),
            inserted_at=value.inserted_at,
            sequence=value.sequence,
            source_batch_id=value.source_batch_id,
        )


class EventPageApiResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    offset: int
    limit: int
    returned: int
    total: int | None


class FacetBucketApiResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    value: str
    count: int


class AggregationRequestApiResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    group_by: str
    metric: str
    time_bucket_seconds: int | None = None
    limit: int


class AggregationBucketApiResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    group_value: str | int
    event_count: int
    metric_value: float | None
    sample_count: int | None
    bucket_start_time: datetime | None
    bucket_end_time: datetime | None


class AggregationApiResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    request: AggregationRequestApiResponse
    buckets: tuple[AggregationBucketApiResponse, ...] = ()

    @classmethod
    def from_domain(cls, value: EventAggregationResult) -> "AggregationApiResponse":
        return cls(
            request=AggregationRequestApiResponse(
                group_by=value.request.group_by,
                metric=value.request.metric,
                time_bucket_seconds=value.request.time_bucket_seconds,
                limit=value.request.limit,
            ),
            buckets=tuple(
                AggregationBucketApiResponse(
                    group_value=bucket.group_value,
                    event_count=bucket.event_count,
                    metric_value=bucket.metric_value,
                    sample_count=bucket.sample_count,
                    bucket_start_time=bucket.bucket_start_time,
                    bucket_end_time=bucket.bucket_end_time,
                )
                for bucket in value.buckets
            ),
        )


class QueryApiResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    events: tuple[StoredEventSummaryApiResponse, ...] = ()
    page: EventPageApiResponse
    facets: dict[str, tuple[FacetBucketApiResponse, ...]] = Field(default_factory=dict)
    aggregation: AggregationApiResponse | None = None
    query_duration_ms: float
    snapshot_size: int
    index_used: bool
    candidate_count: int
    warnings: tuple[str, ...] = ()

    @classmethod
    def from_domain(cls, value: EventQueryResult) -> "QueryApiResponse":
        aggregation = (
            AggregationApiResponse.from_domain(value.aggregation)
            if value.aggregation is not None
            else None
        )
        return cls(
            events=tuple(
                StoredEventSummaryApiResponse.from_domain(item)
                for item in value.events
            ),
            page=EventPageApiResponse(
                offset=value.page.offset,
                limit=value.page.limit,
                returned=value.page.returned,
                total=value.page.total,
            ),
            facets={
                key: tuple(
                    FacetBucketApiResponse(value=bucket.value, count=bucket.count)
                    for bucket in buckets
                )
                for key, buckets in value.facets.items()
            },
            aggregation=aggregation,
            query_duration_ms=value.query_duration_ms,
            snapshot_size=value.snapshot_size,
            index_used=value.index_used,
            candidate_count=value.candidate_count,
            warnings=tuple(value.warnings),
        )


class StoreStatisticsApiResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_count: int
    estimated_memory_bytes: int
    max_events: int
    max_estimated_memory_bytes: int | None
    oldest_inserted_at: datetime | None
    newest_inserted_at: datetime | None
    earliest_event_timestamp: datetime | None
    latest_event_timestamp: datetime | None
    index_enabled: bool
    indexed_field_count: int
    duplicate_ignored_count: int
    replaced_count: int
    evicted_count: int
    retention_removed_count: int
    write_count: int
    query_count: int
    delete_count: int
    clear_count: int
    created_at: datetime
    last_write_at: datetime | None
    last_query_at: datetime | None
    last_retention_at: datetime | None

    @classmethod
    def from_domain(cls, value: EventStoreStatistics) -> "StoreStatisticsApiResponse":
        return cls.model_validate(value.model_dump(mode="json"))


class ParseResultApiResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: str
    events: tuple[EventDetailApiResponse, ...] = ()
    errors: tuple[dict[str, Any], ...] = ()

    @classmethod
    def from_domain(cls, value: ParseResult) -> "ParseResultApiResponse":
        return cls(
            status=value.status.value,
            events=tuple(
                EventDetailApiResponse(
                    schema_version=item.schema_version,
                    event_id=item.event_id,
                    timestamp=item.timestamp,
                    ingested_at=item.ingested_at,
                    source_type=item.source_type.value,
                    severity=item.severity.value,
                    event_type=item.event_type,
                    message=item.message,
                    raw_message=item.raw_message,
                    service=item.service,
                    application=item.application,
                    environment=item.environment,
                    host=item.host,
                    source=item.source,
                    trace_id=item.trace_id,
                    correlation_id=item.correlation_id,
                    user_id=item.user_id,
                    client_ip=item.client_ip,
                    server_ip=item.server_ip,
                    http_method=item.http_method,
                    http_path=item.http_path,
                    http_status=item.http_status,
                    duration_ms=item.duration_ms,
                    attributes=dict(item.attributes),
                    tags=tuple(item.tags),
                )
                for item in value.events
            ),
            errors=tuple(error.model_dump(mode="json") for error in value.errors),
        )


class PipelineResultApiResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    success: bool
    event: EventDetailApiResponse | None = None
    parse_result: ParseResultApiResponse | None = None
    normalization_result: dict[str, Any] | None = None
    selection: dict[str, Any] | None = None
    errors: tuple[dict[str, Any], ...] = ()
    warnings: tuple[dict[str, Any], ...] = ()
    stages: tuple[dict[str, Any], ...] = ()
    duration_ms: float
    parser_name: str | None
    parser_version: str | None
    source_type: str | None
    ambiguous: bool
    normalized: bool

    @classmethod
    def from_domain(cls, value: PipelineResult) -> "PipelineResultApiResponse":
        event = None
        if value.event is not None:
            event = EventDetailApiResponse(
                schema_version=value.event.schema_version,
                event_id=value.event.event_id,
                timestamp=value.event.timestamp,
                ingested_at=value.event.ingested_at,
                source_type=value.event.source_type.value,
                severity=value.event.severity.value,
                event_type=value.event.event_type,
                message=value.event.message,
                raw_message=value.event.raw_message,
                service=value.event.service,
                application=value.event.application,
                environment=value.event.environment,
                host=value.event.host,
                source=value.event.source,
                trace_id=value.event.trace_id,
                correlation_id=value.event.correlation_id,
                user_id=value.event.user_id,
                client_ip=value.event.client_ip,
                server_ip=value.event.server_ip,
                http_method=value.event.http_method,
                http_path=value.event.http_path,
                http_status=value.event.http_status,
                duration_ms=value.event.duration_ms,
                attributes=dict(value.event.attributes),
                tags=tuple(value.event.tags),
            )

        parse_result = (
            ParseResultApiResponse.from_domain(value.parse_result)
            if value.parse_result is not None
            else None
        )
        source_type = value.source_type.value if value.source_type is not None else None

        return cls(
            success=value.success,
            event=event,
            parse_result=parse_result,
            normalization_result=(
                value.normalization_result.model_dump(mode="json")
                if value.normalization_result is not None
                else None
            ),
            selection=(
                value.selection.model_dump(mode="json")
                if value.selection is not None
                else None
            ),
            errors=tuple(item.model_dump(mode="json") for item in value.errors),
            warnings=tuple(item.model_dump(mode="json") for item in value.warnings),
            stages=tuple(item.model_dump(mode="json") for item in value.stages),
            duration_ms=value.duration_ms,
            parser_name=value.parser_name,
            parser_version=value.parser_version,
            source_type=source_type,
            ambiguous=value.ambiguous,
            normalized=value.normalized,
        )


class EventWriteResultApiResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: str
    stored_event: StoredEventDetailApiResponse
    evicted_event_ids: tuple[str, ...] = ()

    @classmethod
    def from_domain(cls, value: EventWriteResult) -> "EventWriteResultApiResponse":
        return cls(
            status=value.status,
            stored_event=StoredEventDetailApiResponse.from_domain(value.stored_event),
            evicted_event_ids=tuple(value.evicted_event_ids),
        )


class BatchWriteResultApiResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    inserted: tuple[StoredEventDetailApiResponse, ...] = ()
    ignored_event_ids: tuple[str, ...] = ()
    replaced: tuple[StoredEventDetailApiResponse, ...] = ()
    evicted_event_ids: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    atomic: bool

    @classmethod
    def from_domain(cls, value: BatchWriteResult) -> "BatchWriteResultApiResponse":
        return cls(
            inserted=tuple(
                StoredEventDetailApiResponse.from_domain(item)
                for item in value.inserted
            ),
            ignored_event_ids=tuple(value.ignored_event_ids),
            replaced=tuple(
                StoredEventDetailApiResponse.from_domain(item)
                for item in value.replaced
            ),
            evicted_event_ids=tuple(value.evicted_event_ids),
            errors=tuple(value.errors),
            atomic=value.atomic,
        )


class BatchParseResultApiResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    events: tuple[EventDetailApiResponse, ...] = ()
    failures: tuple[dict[str, Any], ...] = ()
    statistics: dict[str, Any]
    sessions: tuple[dict[str, Any], ...] = ()
    warnings: tuple[str, ...] = ()
    source_id: str | None = None

    @classmethod
    def from_domain(cls, value: BatchParseResult) -> "BatchParseResultApiResponse":
        return cls(
            events=tuple(
                EventDetailApiResponse(
                    schema_version=item.schema_version,
                    event_id=item.event_id,
                    timestamp=item.timestamp,
                    ingested_at=item.ingested_at,
                    source_type=item.source_type.value,
                    severity=item.severity.value,
                    event_type=item.event_type,
                    message=item.message,
                    raw_message=item.raw_message,
                    service=item.service,
                    application=item.application,
                    environment=item.environment,
                    host=item.host,
                    source=item.source,
                    trace_id=item.trace_id,
                    correlation_id=item.correlation_id,
                    user_id=item.user_id,
                    client_ip=item.client_ip,
                    server_ip=item.server_ip,
                    http_method=item.http_method,
                    http_path=item.http_path,
                    http_status=item.http_status,
                    duration_ms=item.duration_ms,
                    attributes=dict(item.attributes),
                    tags=tuple(item.tags),
                )
                for item in value.events
            ),
            failures=tuple(item.model_dump(mode="json") for item in value.failures),
            statistics=value.statistics.model_dump(mode="json"),
            sessions=tuple(item.model_dump(mode="json") for item in value.sessions),
            warnings=tuple(value.warnings),
            source_id=value.source_id,
        )
