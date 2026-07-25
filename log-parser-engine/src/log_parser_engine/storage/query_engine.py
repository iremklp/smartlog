
from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime
from functools import cmp_to_key
from typing import Any, Sequence

from log_parser_engine.models import (
    EventAggregationRequest,
    EventAggregationResult,
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

# For sorting severities
SEVERITY_ORDER = {
    LogSeverity.TRACE: 1,
    LogSeverity.DEBUG: 2,
    LogSeverity.INFO: 3,
    LogSeverity.WARNING: 4,
    LogSeverity.ERROR: 5,
    LogSeverity.CRITICAL: 6,
    LogSeverity.UNKNOWN: 7,
}


class InMemoryEventQueryEngine:
    """
    Executes queries against a snapshot of in-memory event data.
    This class is stateless and operates on the data provided to it.
    """

    def __init__(
        self,
        options: EventStoreOptions,
        query: EventQuery,
        events: dict[str, StoredEvent],
        indexes: dict[str, dict[Any, set[str]]],
        timestamp_index: list[tuple[datetime, int, str]],
    ):
        self._options = options
        self._query = query
        self._all_events = events
        self._indexes = indexes
        self._timestamp_index = timestamp_index
        self._start_time = time.monotonic()

    def execute(self) -> EventQueryResult:
        """Executes the query and returns the result."""
        
        candidate_ids, index_used = self._get_candidate_ids_from_indexes()
        
        filtered_events = self._filter_events(candidate_ids)
        
        sorted_events = self._sort_events(filtered_events)
        
        total_matches = len(sorted_events)

        # Pagination
        limit = self._query.limit or self._options.default_page_size
        offset = self._query.offset
        paginated_events = sorted_events[offset : offset + limit]

        # Facets
        facets = self._calculate_facets(sorted_events) if self._query.include_facets else {}

        # Aggregation
        aggregation_result = self._calculate_aggregation(sorted_events) if self._query.aggregation else None

        duration_ms = (time.monotonic() - self._start_time) * 1000

        return EventQueryResult(
            events=tuple(paginated_events) if self._query.include_events else tuple(),
            page=EventPage(
                offset=offset,
                limit=limit,
                returned=len(paginated_events),
                total=total_matches if self._query.include_total else None,
            ),
            facets=facets,
            aggregation=aggregation_result,
            query_duration_ms=duration_ms,
            snapshot_size=len(self._all_events),
            index_used=index_used,
            candidate_count=len(candidate_ids) if candidate_ids is not None else len(self._all_events),
            warnings=tuple(),
        )

    def _get_candidate_ids_from_indexes(self) -> tuple[set[str] | None, bool]:
        """Uses indexes to narrow down the set of events to scan."""
        if not self._options.enable_indexes:
            return None, False

        candidate_sets: list[set[str]] = []

        q_filter = self._query.filter

        # Simple indexed fields
        simple_fields = ["severities", "source_types", "event_types", "parser_names", "hosts", "services"]
        for field in simple_fields:
            values = getattr(q_filter, field)
            if values:
                ids = set()
                index = self._indexes.get(field.rstrip('s'), {})
                for val in values:
                    ids.update(index.get(val.value if hasattr(val, 'value') else val, set()))
                candidate_sets.append(ids)
        
        if not candidate_sets:
            return None, False # No indexable filters were used

        # Intersect all candidate sets to get the final list
        final_candidates = candidate_sets[0]
        for i in range(1, len(candidate_sets)):
            final_candidates.intersection_update(candidate_sets[i])
            if not final_candidates:
                break
        
        return final_candidates, True
    
    def _filter_events(self, candidate_ids: set[str] | None) -> list[StoredEvent]:
        """Applies all filters to the candidate events."""
        events_to_scan = [self._all_events[i] for i in candidate_ids] if candidate_ids is not None else list(self._all_events.values())
        
        if not events_to_scan:
            return []
            
        q_filter = self._query.filter
        filtered = []

        for event in events_to_scan:
            # Note: Filters already applied by index are re-applied here for correctness.
            # This is a trade-off for simplicity over pure performance.
            if q_filter.event_ids and event.id not in q_filter.event_ids: continue
            if q_filter.exclude_event_ids and event.id in q_filter.exclude_event_ids: continue
            if q_filter.start_time and event.timestamp < q_filter.start_time: continue
            if q_filter.end_time and event.timestamp >= q_filter.end_time: continue
            if q_filter.severities and event.severity not in q_filter.severities: continue
            
            # More filters...
            if q_filter.tags_any and not any(t in event.event.tags for t in q_filter.tags_any): continue
            if q_filter.tags_all and not all(t in event.event.tags for t in q_filter.tags_all): continue

            if q_filter.message_contains:
                msg = event.event.message
                search_term = q_filter.message_contains
                if not q_filter.message_case_sensitive:
                    msg = msg.casefold()
                    search_term = search_term.casefold()
                if search_term not in msg:
                    continue

            if q_filter.attribute_exists:
                if not all(resolve_attribute_path(event.event, p)[0] for p in q_filter.attribute_exists):
                    continue
            
            if q_filter.attribute_equals:
                match = True
                for path, val in q_filter.attribute_equals.items():
                    found, resolved_val = resolve_attribute_path(event.event, path)
                    if not found or resolved_val != val:
                        match = False
                        break
                if not match:
                    continue
            
            filtered.append(event)
            
        return filtered

    def _sort_events(self, events: list[StoredEvent]) -> list[StoredEvent]:
        """Sorts the events based on the query's sort criteria."""
        if not self._query.sort:
            # Default sort: timestamp desc, sequence desc
            return sorted(events, key=lambda e: (e.timestamp, e.sequence), reverse=True)

        def compare_events(a: StoredEvent, b: StoredEvent) -> int:
            for s in self._query.sort:
                val_a = getattr(a.event, s.field) if hasattr(a.event, s.field) else getattr(a, s.field)
                val_b = getattr(b.event, s.field) if hasattr(b.event, s.field) else getattr(b, s.field)
                
                # Handle severity sorting
                if s.field == "severity":
                    val_a, val_b = SEVERITY_ORDER.get(val_a, 99), SEVERITY_ORDER.get(val_b, 99)

                if val_a < val_b:
                    return -1 if s.direction == "asc" else 1
                if val_a > val_b:
                    return 1 if s.direction == "asc" else -1
            
            # Tie-breaker
            if a.sequence < b.sequence: return 1
            if a.sequence > b.sequence: return -1
            return 0

        return sorted(events, key=cmp_to_key(compare_events))

    def _calculate_facets(self, events: list[StoredEvent]) -> dict[str, tuple[FacetBucket, ...]]:
        """Calculates facet counts for the filtered events."""
        facets = defaultdict(lambda: defaultdict(int))
        
        for event in events:
            for field in self._query.facet_fields:
                if field == "tags":
                    for tag in event.event.tags:
                        facets[field][tag] += 1
                else:
                    value = getattr(event.event, field, None)
                    if value is not None:
                        key = value.value if hasattr(value, "value") else str(value)
                        facets[field][key] += 1
        
        result = {}
        for field, counts in facets.items():
            buckets = [FacetBucket(value=v, count=c) for v, c in counts.items()]
            # Sort by count desc, then value asc
            buckets.sort(key=lambda b: (-b.count, b.value))
            result[field] = tuple(buckets[:100]) # Limit to 100 buckets

        return result
        
    def _calculate_aggregation(self, events: list[StoredEvent]) -> EventAggregationResult | None:
        """Calculates aggregations for the filtered events."""
        agg_request = self._query.aggregation
        if not agg_request or not events:
            return None

        buckets = defaultdict(lambda: {"count": 0, "sum_duration": 0.0, "samples": 0})

        for event in events:
            group_keys = self._get_group_keys_for_event(event, agg_request.group_by)
            for key in group_keys:
                buckets[key]["count"] += 1
                if agg_request.metric != "count" and event.event.duration_ms is not None:
                    buckets[key]["sum_duration"] += event.event.duration_ms
                    buckets[key]["samples"] += 1
        
        result_buckets = []
        for key, data in buckets.items():
            metric_value = None
            if agg_request.metric == "count":
                metric_value = data["count"]
            elif agg_request.metric == "sum_duration_ms":
                metric_value = data["sum_duration"]
            elif agg_request.metric == "average_duration_ms":
                metric_value = (data["sum_duration"] / data["samples"]) if data["samples"] > 0 else 0.0

            result_buckets.append(AggregationBucket(
                group_value=key,
                event_count=data["count"],
                metric_value=metric_value,
                sample_count=data["samples"] if agg_request.metric != "count" else None
            ))

        # Sort buckets
        result_buckets.sort(key=lambda b: b.metric_value or 0, reverse=True)

        return EventAggregationResult(
            request=agg_request,
            buckets=tuple(result_buckets[:agg_request.limit])
        )

    def _get_group_keys_for_event(self, event: StoredEvent, group_by_field: str) -> list[Any]:
        """Gets the key(s) for an event for a given group_by field."""
        if group_by_field == "tag":
            return event.event.tags
        
        # For all other fields, it's a single value
        val = getattr(event.event, group_by_field, None)
        if val is None:
            return []
        
        return [val.value if hasattr(val, "value") else val]

