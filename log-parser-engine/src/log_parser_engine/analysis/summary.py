from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from datetime import datetime

from log_parser_engine.exceptions.analysis import (
    AnalysisEventLimitError,
    AnalysisGroupLimitError,
    AnalysisNumericValueError,
)
from log_parser_engine.models.analysis_summary import AnalysisSummary
from log_parser_engine.models.enums import LogSeverity
from log_parser_engine.models.stored_event import StoredEvent

from .extractors import (
    extract_duration_ms,
    get_event_type,
    get_host,
    get_http_status,
    get_parser_name,
    get_service,
    get_severity,
    get_source_type,
)
from .helpers import bounded_dimension, normalized_text, safe_ratio
from .options import AnalysisOptions
from .validation import validate_stored_events


def _add_bounded_unique(
    values: set[str],
    value: str | None,
    *,
    field: str,
    options: AnalysisOptions,
) -> None:
    if value is None or value in values:
        return
    if len(values) >= options.max_groups:
        raise AnalysisGroupLimitError(
            field,
            len(values) + 1,
            options.max_groups,
        )
    values.add(value)


def summarize_events(
    events: Sequence[StoredEvent],
    *,
    input_event_count: int | None = None,
    duration_field: str | None = None,
    status_field: str | None = None,
    options: AnalysisOptions | None = None,
) -> AnalysisSummary:
    """Build exact high-level counters for an immutable event snapshot."""
    resolved_options = options or AnalysisOptions()
    validate_stored_events(events)
    matched_count = len(events)
    if matched_count > resolved_options.max_events:
        raise AnalysisEventLimitError(
            matched_count,
            resolved_options.max_events,
        )
    input_count = matched_count if input_event_count is None else input_event_count
    if input_count < matched_count:
        raise ValueError("input_event_count cannot be below matched event count")

    severity_counts: Counter[str] = Counter()
    event_types: set[str] = set()
    services: set[str] = set()
    hosts: set[str] = set()
    parsers: set[str] = set()
    source_types: set[str] = set()
    seen_content_hashes: set[str] = set()
    duplicate_content_count = 0
    events_with_duration = 0
    events_with_http_status = 0
    out_of_order = 0
    previous_timestamp: datetime | None = None
    earliest: datetime | None = None
    latest: datetime | None = None

    for stored in events:
        severity = get_severity(stored)
        if severity == LogSeverity.TRACE:
            severity_counts["trace"] += 1
        elif severity == LogSeverity.DEBUG:
            severity_counts["debug"] += 1
        elif severity in (LogSeverity.INFO, LogSeverity.NOTICE):
            severity_counts["info"] += 1
        elif severity == LogSeverity.WARNING:
            severity_counts["warning"] += 1
        elif severity == LogSeverity.ERROR:
            severity_counts["error"] += 1
        elif severity in (LogSeverity.CRITICAL, LogSeverity.FATAL):
            severity_counts["critical"] += 1
        else:
            severity_counts["unknown"] += 1

        for field, target, value in (
            ("event_type", event_types, get_event_type(stored)),
            ("service", services, get_service(stored)),
            ("host", hosts, get_host(stored)),
            ("parser", parsers, get_parser_name(stored)),
            (
                "source_type",
                source_types,
                normalized_text(get_source_type(stored)),
            ),
        ):
            _add_bounded_unique(
                target,
                bounded_dimension(
                    value,
                    limit=resolved_options.max_dimension_value_length,
                ),
                field=field,
                options=resolved_options,
            )

        duration = extract_duration_ms(
            stored,
            explicit_field=duration_field,
            candidates=resolved_options.duration_field_candidates,
            max_depth=resolved_options.max_attribute_depth,
            strict=resolved_options.strict_numeric_values,
        )
        if (
            duration.found
            and not duration.valid
            and not resolved_options.ignore_non_finite_values
        ):
            raise AnalysisNumericValueError(
                "duration field contains an invalid numeric value"
            )
        if duration.valid:
            events_with_duration += 1
        if (
            get_http_status(
                stored,
                explicit_field=status_field,
                candidates=resolved_options.http_status_field_candidates,
                max_depth=resolved_options.max_attribute_depth,
            )
            is not None
        ):
            events_with_http_status += 1

        if stored.content_hash in seen_content_hashes:
            duplicate_content_count += 1
        else:
            seen_content_hashes.add(stored.content_hash)
        if previous_timestamp is not None and stored.timestamp < previous_timestamp:
            out_of_order += 1
        previous_timestamp = stored.timestamp
        earliest = (
            stored.timestamp
            if earliest is None
            else min(earliest, stored.timestamp)
        )
        latest = (
            stored.timestamp
            if latest is None
            else max(latest, stored.timestamp)
        )

    error_count = severity_counts["error"]
    critical_count = severity_counts["critical"]
    error_or_critical = error_count + critical_count
    span = (
        (latest - earliest).total_seconds()
        if earliest is not None and latest is not None
        else None
    )
    events_per_second = (
        matched_count / span if span is not None and span > 0 else None
    )
    return AnalysisSummary(
        input_event_count=input_count,
        matched_event_count=matched_count,
        trace_count=severity_counts["trace"],
        debug_count=severity_counts["debug"],
        info_count=severity_counts["info"],
        warning_count=severity_counts["warning"],
        error_count=error_count,
        critical_count=critical_count,
        unknown_count=severity_counts["unknown"],
        error_or_critical_count=error_or_critical,
        error_rate=safe_ratio(error_or_critical, matched_count),
        critical_rate=safe_ratio(critical_count, matched_count),
        unique_event_type_count=len(event_types),
        unique_service_count=len(services),
        unique_host_count=len(hosts),
        unique_parser_count=len(parsers),
        unique_source_type_count=len(source_types),
        earliest_timestamp=earliest,
        latest_timestamp=latest,
        time_span_seconds=span,
        events_per_second=events_per_second,
        events_per_minute=(
            events_per_second * 60.0
            if events_per_second is not None
            else None
        ),
        events_with_duration=events_with_duration,
        events_with_http_status=events_with_http_status,
        duplicate_content_count=duplicate_content_count,
        out_of_order_timestamp_count=out_of_order,
    )
