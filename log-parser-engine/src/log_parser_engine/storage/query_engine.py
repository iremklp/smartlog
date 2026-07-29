from __future__ import annotations

import bisect
import math
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from functools import cmp_to_key
from typing import Any

from log_parser_engine.exceptions import EventPaginationError
from log_parser_engine.models import (
    EventAggregationRequest,
    EventAggregationResult,
    EventFilter,
    EventPage,
    EventQuery,
    EventQueryResult,
    FacetBucket,
    LogSeverity,
    StoredEvent,
)
from log_parser_engine.models.event_aggregation import AggregationBucket

from .helpers import resolve_attribute_path
from .options import EventStoreOptions

SEVERITY_ORDER: dict[LogSeverity, int] = {
    LogSeverity.TRACE: 1,
    LogSeverity.DEBUG: 2,
    LogSeverity.INFO: 3,
    LogSeverity.NOTICE: 4,
    LogSeverity.WARNING: 5,
    LogSeverity.ERROR: 6,
    LogSeverity.CRITICAL: 7,
    LogSeverity.FATAL: 8,
    LogSeverity.UNKNOWN: 9,
}

_FILTER_TO_INDEX_FIELD = {
    "severities": "severity",
    "source_types": "source_type",
    "event_types": "event_type",
    "parser_names": "parser_name",
    "hosts": "host",
    "services": "service",
}


@dataclass(slots=True)
class _AggregationAccumulator:
    event_count: int = 0
    duration_sum: float = 0.0
    sample_count: int = 0


@dataclass(frozen=True, slots=True)
class _AggregationGroup:
    value: str | int
    start_time: datetime | None = None
    end_time: datetime | None = None


def _event_field_value(event: StoredEvent, field: str) -> object | None:
    if field == "parser_name":
        parser_name = event.event.attributes.get("parser_name")
        return parser_name if isinstance(parser_name, str) else None
    if field == "timestamp":
        return event.timestamp
    if field == "inserted_at":
        return event.inserted_at
    if field == "sequence":
        return event.sequence
    if field == "severity":
        return event.severity
    if field == "source_type":
        return event.event.source_type
    if field == "event_type":
        return event.event.event_type
    if field == "host":
        return event.event.host
    if field == "service":
        return event.event.service
    return None


def matches_event_filter(
    event: StoredEvent,
    event_filter: EventFilter,
) -> bool:
    """Return whether an event satisfies every typed filter criterion."""

    log_event = event.event
    if event_filter.event_ids and event.id not in event_filter.event_ids:
        return False
    if (
        event_filter.exclude_event_ids
        and event.id in event_filter.exclude_event_ids
    ):
        return False
    if event_filter.start_time and event.timestamp < event_filter.start_time:
        return False
    if event_filter.end_time and event.timestamp >= event_filter.end_time:
        return False
    if (
        event_filter.severities
        and event.severity not in event_filter.severities
    ):
        return False
    if (
        event_filter.source_types
        and log_event.source_type not in event_filter.source_types
    ):
        return False
    if (
        event_filter.event_types
        and log_event.event_type not in event_filter.event_types
    ):
        return False

    parser_name = _event_field_value(event, "parser_name")
    if (
        event_filter.parser_names
        and parser_name not in event_filter.parser_names
    ):
        return False
    if event_filter.hosts and log_event.host not in event_filter.hosts:
        return False
    if event_filter.services and log_event.service not in event_filter.services:
        return False
    if (
        event_filter.client_ips
        and log_event.client_ip not in event_filter.client_ips
    ):
        return False
    if event_filter.user_ids and log_event.user_id not in event_filter.user_ids:
        return False
    if (
        event_filter.correlation_ids
        and log_event.correlation_id not in event_filter.correlation_ids
    ):
        return False

    if event_filter.tags_any and not any(
        tag in log_event.tags for tag in event_filter.tags_any
    ):
        return False
    if event_filter.tags_all and not all(
        tag in log_event.tags for tag in event_filter.tags_all
    ):
        return False

    if event_filter.message_contains:
        message = log_event.message
        search_term = event_filter.message_contains
        if not event_filter.message_case_sensitive:
            message = message.casefold()
            search_term = search_term.casefold()
        if search_term not in message:
            return False

    if event_filter.attribute_exists and not all(
        resolve_attribute_path(log_event, path)[0]
        for path in event_filter.attribute_exists
    ):
        return False
    for path, expected in event_filter.attribute_equals.items():
        found, value = resolve_attribute_path(log_event, path)
        if not found or value != expected:
            return False
    return True


class InMemoryEventQueryEngine:
    """Execute a typed query against an immutable-reference store snapshot."""

    def __init__(
        self,
        options: EventStoreOptions,
        query: EventQuery,
        events: dict[str, StoredEvent],
        indexes: dict[str, dict[Any, set[str]]],
        timestamp_index: list[tuple[datetime, int, str]],
    ) -> None:
        self._options = options
        self._query = query
        self._all_events = events
        self._indexes = indexes
        self._timestamp_index = timestamp_index

    def execute(self) -> EventQueryResult:
        """Execute filtering, sorting, pagination, facets and aggregation."""

        started_at = time.perf_counter()
        limit = self._resolve_limit()
        candidate_ids, index_used = self._get_candidate_ids_from_indexes()
        filtered_events = self._filter_events(candidate_ids)
        sorted_events = self._sort_events(filtered_events)
        total_matches = len(sorted_events)
        offset = self._query.offset
        paginated_events = sorted_events[offset : offset + limit]

        facets = (
            self._calculate_facets(sorted_events)
            if self._query.include_facets
            else {}
        )
        aggregation = self._calculate_aggregation(sorted_events)
        candidate_count = (
            len(candidate_ids)
            if candidate_ids is not None
            else len(self._all_events)
        )

        return EventQueryResult(
            events=(
                tuple(paginated_events)
                if self._query.include_events
                else ()
            ),
            page=EventPage(
                offset=offset,
                limit=limit,
                returned=len(paginated_events),
                total=(
                    total_matches
                    if self._query.include_total
                    else None
                ),
            ),
            facets=facets,
            aggregation=aggregation,
            query_duration_ms=(time.perf_counter() - started_at) * 1_000,
            snapshot_size=len(self._all_events),
            index_used=index_used,
            candidate_count=candidate_count,
        )

    def _resolve_limit(self) -> int:
        limit = (
            self._query.limit
            if self._query.limit is not None
            else self._options.default_page_size
        )
        allowed_limit = min(
            self._options.max_page_size,
            self._options.max_query_limit,
        )
        if limit > allowed_limit:
            raise EventPaginationError(
                "query limit exceeds the configured maximum"
            )
        return limit

    def _get_candidate_ids_from_indexes(
        self,
    ) -> tuple[set[str] | None, bool]:
        if not self._options.enable_indexes:
            return None, False

        candidate_sets: list[set[str]] = []
        query_filter = self._query.filter

        if query_filter.event_ids:
            candidate_sets.append(
                set(query_filter.event_ids).intersection(self._all_events)
            )

        configured_fields = set(self._options.indexed_fields)
        for filter_field, index_field in _FILTER_TO_INDEX_FIELD.items():
            if index_field not in configured_fields:
                continue
            values = getattr(query_filter, filter_field)
            if not values:
                continue
            index = self._indexes.get(index_field, {})
            matching_ids: set[str] = set()
            for value in values:
                matching_ids.update(
                    index.get(self._normalize_index_key(value), set())
                )
            candidate_sets.append(matching_ids)

        if "tags" in configured_fields:
            self._append_tag_candidate_sets(candidate_sets, query_filter)

        if query_filter.start_time or query_filter.end_time:
            candidate_sets.append(
                self._timestamp_candidate_ids(
                    query_filter.start_time,
                    query_filter.end_time,
                )
            )

        if not candidate_sets:
            return None, False

        final_candidates = candidate_sets[0].copy()
        for candidates in candidate_sets[1:]:
            final_candidates.intersection_update(candidates)
            if not final_candidates:
                break
        return final_candidates, True

    def _append_tag_candidate_sets(
        self,
        candidate_sets: list[set[str]],
        event_filter: EventFilter,
    ) -> None:
        tag_index = self._indexes.get("tags", {})
        if event_filter.tags_any:
            any_ids: set[str] = set()
            for tag in event_filter.tags_any:
                any_ids.update(tag_index.get(tag, set()))
            candidate_sets.append(any_ids)

        if event_filter.tags_all:
            all_ids: set[str] | None = None
            for tag in event_filter.tags_all:
                tag_ids = set(tag_index.get(tag, set()))
                if all_ids is None:
                    all_ids = tag_ids
                else:
                    all_ids.intersection_update(tag_ids)
            candidate_sets.append(all_ids or set())

    def _timestamp_candidate_ids(
        self,
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> set[str]:
        left = 0
        right = len(self._timestamp_index)
        if start_time is not None:
            left = bisect.bisect_left(
                self._timestamp_index,
                (start_time, -1, ""),
            )
        if end_time is not None:
            right = bisect.bisect_left(
                self._timestamp_index,
                (end_time, -1, ""),
            )
        return {
            event_id
            for _, _, event_id in self._timestamp_index[left:right]
        }

    @staticmethod
    def _normalize_index_key(value: object) -> object:
        if isinstance(value, Enum):
            return value.value
        return value

    def _filter_events(
        self,
        candidate_ids: set[str] | None,
    ) -> list[StoredEvent]:
        if candidate_ids is None:
            events_to_scan = list(self._all_events.values())
        else:
            events_to_scan = [
                self._all_events[event_id]
                for event_id in candidate_ids
                if event_id in self._all_events
            ]
        return [
            event
            for event in events_to_scan
            if matches_event_filter(event, self._query.filter)
        ]

    def _sort_events(
        self,
        events: list[StoredEvent],
    ) -> list[StoredEvent]:
        if not self._query.sort:
            return sorted(
                events,
                key=lambda event: (event.timestamp, event.sequence),
                reverse=True,
            )

        def compare_events(left: StoredEvent, right: StoredEvent) -> int:
            for criterion in self._query.sort:
                left_value = self._sort_value(left, criterion.field)
                right_value = self._sort_value(right, criterion.field)
                comparison = self._compare_optional_values(
                    left_value,
                    right_value,
                )
                if comparison:
                    if (
                        left_value is None
                        or right_value is None
                        or criterion.direction == "asc"
                    ):
                        return comparison
                    return -comparison

            if left.sequence < right.sequence:
                return 1
            if left.sequence > right.sequence:
                return -1
            return 0

        return sorted(events, key=cmp_to_key(compare_events))

    @staticmethod
    def _sort_value(
        event: StoredEvent,
        field: str,
    ) -> datetime | int | str | None:
        value = _event_field_value(event, field)
        if field == "severity" and isinstance(value, LogSeverity):
            return SEVERITY_ORDER[value]
        if isinstance(value, Enum):
            return str(value.value)
        if isinstance(value, (datetime, int, str)):
            return value
        return None

    @staticmethod
    def _compare_optional_values(
        left: datetime | int | str | None,
        right: datetime | int | str | None,
    ) -> int:
        if left is None and right is None:
            return 0
        if left is None:
            return 1
        if right is None:
            return -1
        if isinstance(left, datetime) and isinstance(right, datetime):
            return (left > right) - (left < right)
        if isinstance(left, int) and isinstance(right, int):
            return (left > right) - (left < right)
        left_text = str(left)
        right_text = str(right)
        return (left_text > right_text) - (left_text < right_text)

    def _calculate_facets(
        self,
        events: list[StoredEvent],
    ) -> dict[str, tuple[FacetBucket, ...]]:
        result: dict[str, tuple[FacetBucket, ...]] = {}
        for field in self._query.facet_fields:
            counts: dict[str, int] = {}
            for event in events:
                for value in self._facet_values(event, field):
                    counts[value] = counts.get(value, 0) + 1
            buckets = [
                FacetBucket(value=value, count=count)
                for value, count in counts.items()
            ]
            buckets.sort(key=lambda bucket: (-bucket.count, bucket.value))
            result[field] = tuple(
                buckets[: self._options.max_facet_buckets]
            )
        return result

    @staticmethod
    def _facet_values(
        event: StoredEvent,
        field: str,
    ) -> tuple[str, ...]:
        if field == "tags":
            return tuple(event.event.tags)
        value = _event_field_value(event, field)
        if value is None:
            return ()
        if isinstance(value, Enum):
            return (str(value.value),)
        if isinstance(value, (str, int, float, bool)):
            return (str(value),)
        return ()

    def _calculate_aggregation(
        self,
        events: list[StoredEvent],
    ) -> EventAggregationResult | None:
        request = self._query.aggregation
        if request is None:
            return None

        accumulators: dict[
            _AggregationGroup,
            _AggregationAccumulator,
        ] = {}
        for event in events:
            groups = self._groups_for_event(event, request)
            for group in groups:
                accumulator = accumulators.setdefault(
                    group,
                    _AggregationAccumulator(),
                )
                accumulator.event_count += 1
                duration = event.event.duration_ms
                if (
                    request.metric != "count"
                    and duration is not None
                    and math.isfinite(duration)
                ):
                    accumulator.duration_sum += duration
                    accumulator.sample_count += 1

        buckets = [
            self._build_aggregation_bucket(request, group, accumulator)
            for group, accumulator in accumulators.items()
        ]
        if request.group_by == "time_bucket":
            buckets.sort(
                key=lambda bucket: (
                    bucket.bucket_start_time
                    if bucket.bucket_start_time is not None
                    else datetime.max.replace(tzinfo=timezone.utc)
                )
            )
        else:
            buckets.sort(key=self._aggregation_sort_key)

        return EventAggregationResult(
            request=request,
            buckets=tuple(buckets[: request.limit]),
        )

    @staticmethod
    def _build_aggregation_bucket(
        request: EventAggregationRequest,
        group: _AggregationGroup,
        accumulator: _AggregationAccumulator,
    ) -> AggregationBucket:
        metric_value: float | None
        sample_count: int | None
        if request.metric == "count":
            metric_value = float(accumulator.event_count)
            sample_count = None
        elif request.metric == "sum_duration_ms":
            metric_value = accumulator.duration_sum
            sample_count = accumulator.sample_count
        elif accumulator.sample_count:
            metric_value = (
                accumulator.duration_sum / accumulator.sample_count
            )
            sample_count = accumulator.sample_count
        else:
            metric_value = None
            sample_count = 0

        return AggregationBucket(
            group_value=group.value,
            event_count=accumulator.event_count,
            metric_value=metric_value,
            sample_count=sample_count,
            bucket_start_time=group.start_time,
            bucket_end_time=group.end_time,
        )

    @staticmethod
    def _aggregation_sort_key(
        bucket: AggregationBucket,
    ) -> tuple[int, float, str]:
        if bucket.metric_value is None:
            return (1, 0.0, str(bucket.group_value))
        return (
            0,
            -bucket.metric_value,
            str(bucket.group_value),
        )

    @staticmethod
    def _groups_for_event(
        event: StoredEvent,
        request: EventAggregationRequest,
    ) -> tuple[_AggregationGroup, ...]:
        if request.group_by == "tag":
            return tuple(
                _AggregationGroup(value=tag)
                for tag in event.event.tags
            )
        if request.group_by == "time_bucket":
            seconds = request.time_bucket_seconds
            if seconds is None:  # pragma: no cover - model invariant
                return ()
            timestamp = event.timestamp.astimezone(timezone.utc)
            epoch = math.floor(timestamp.timestamp() / seconds) * seconds
            start = datetime.fromtimestamp(epoch, tz=timezone.utc)
            end = start + timedelta(seconds=seconds)
            return (
                _AggregationGroup(
                    value=start.isoformat(),
                    start_time=start,
                    end_time=end,
                ),
            )

        value = _event_field_value(event, request.group_by)
        if isinstance(value, Enum):
            value = value.value
        if not isinstance(value, (str, int)):
            return ()
        return (_AggregationGroup(value=value),)
