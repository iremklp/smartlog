from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from log_parser_engine.exceptions.analysis import (
    AnalysisFieldResolutionError,
    AnalysisGroupLimitError,
)
from log_parser_engine.models.distribution import DistributionResult
from log_parser_engine.models.stored_event import StoredEvent

from .extractors import (
    get_event_type,
    get_host,
    get_http_method,
    get_http_status,
    get_parser_name,
    get_service,
    get_severity,
    get_source_type,
    get_tags,
    http_status_class,
)
from .helpers import bounded_dimension, normalized_text
from .options import AnalysisOptions
from .ranking import ranked_items
from .validation import (
    resolve_event_field,
    validate_field_path,
    validate_stored_events,
)

SUPPORTED_DISTRIBUTIONS = frozenset(
    {
        "severity",
        "source_type",
        "event_type",
        "parser",
        "parser_name",
        "host",
        "service",
        "tag",
        "tags",
        "http_method",
        "method",
        "http_status",
        "status_code",
        "status_class",
    }
)


def _extract_values(
    event: StoredEvent,
    *,
    field: str,
    options: AnalysisOptions,
) -> tuple[str, ...]:
    if field == "severity":
        return (get_severity(event).value,)
    if field == "source_type":
        return (get_source_type(event).value,)
    if field == "event_type":
        value = get_event_type(event)
    elif field in {"parser", "parser_name"}:
        value = get_parser_name(event)
    elif field == "host":
        value = get_host(event)
    elif field == "service":
        value = get_service(event)
    elif field in {"tag", "tags"}:
        return tuple(
            value
            for tag in dict.fromkeys(get_tags(event))
            if (
                value := bounded_dimension(
                    tag,
                    limit=options.max_dimension_value_length,
                )
            )
            is not None
        )
    elif field in {"http_method", "method"}:
        value = get_http_method(
            event,
            candidates=options.http_method_field_candidates,
            max_depth=options.max_attribute_depth,
        )
    elif field in {"http_status", "status_code"}:
        status = get_http_status(
            event,
            candidates=options.http_status_field_candidates,
            max_depth=options.max_attribute_depth,
        )
        value = str(status) if status is not None else None
    elif field == "status_class":
        status = get_http_status(
            event,
            candidates=options.http_status_field_candidates,
            max_depth=options.max_attribute_depth,
        )
        value = http_status_class(status) if status is not None else None
    else:
        found, raw_value = resolve_event_field(
            event.event,
            field,
            max_depth=options.max_attribute_depth,
        )
        value = normalized_text(raw_value) if found else None
    bounded_value = bounded_dimension(
        value,
        limit=options.max_dimension_value_length,
    )
    return (bounded_value,) if bounded_value is not None else ()


def build_distribution(
    events: Sequence[StoredEvent],
    *,
    field: str,
    top_n: int,
    options: AnalysisOptions | None = None,
) -> DistributionResult:
    """Build an exact, bounded categorical distribution."""
    resolved_options = options or AnalysisOptions()
    validate_stored_events(events)
    if top_n <= 0 or top_n > resolved_options.max_top_n:
        raise ValueError("top_n is outside the configured bounds")
    cleaned_field = field.strip()
    if not cleaned_field:
        raise ValueError("field must not be empty")
    if cleaned_field in {"message", "raw_message"}:
        raise AnalysisFieldResolutionError(
            "message content cannot be used as a distribution key"
        )
    if cleaned_field not in SUPPORTED_DISTRIBUTIONS:
        try:
            validate_field_path(
                cleaned_field,
                max_depth=resolved_options.max_attribute_depth,
            )
        except ValueError as exc:
            raise AnalysisFieldResolutionError(
                "distribution field path is unsafe"
            ) from exc

    counts: Counter[str] = Counter()
    missing_count = 0
    matched_value_count = 0
    for event in events:
        values = _extract_values(event, field=cleaned_field, options=resolved_options)
        if not values:
            missing_count += 1
            continue
        matched_value_count += len(values)
        for value in values:
            if value not in counts and len(counts) >= resolved_options.max_groups:
                raise AnalysisGroupLimitError(
                    cleaned_field,
                    len(counts) + 1,
                    resolved_options.max_groups,
                )
            counts[value] += 1

    items, other_count, truncated = ranked_items(
        counts,
        total_count=len(events),
        top_n=top_n,
    )
    return DistributionResult(
        field=cleaned_field,
        total_count=len(events),
        matched_value_count=matched_value_count,
        missing_count=missing_count,
        unique_value_count=len(counts),
        items=items,
        other_count=other_count,
        truncated=truncated,
    )


def build_distributions(
    events: Sequence[StoredEvent],
    *,
    fields: Sequence[str],
    top_n: int,
    options: AnalysisOptions | None = None,
) -> tuple[DistributionResult, ...]:
    """Build distributions in request order with duplicate fields removed."""
    resolved_options = options or AnalysisOptions()
    unique_fields = tuple(
        dict.fromkeys(field.strip() for field in fields if field.strip())
    )
    if len(unique_fields) > resolved_options.max_group_fields_per_request:
        raise AnalysisFieldResolutionError(
            "distribution field count exceeds the configured limit"
        )
    return tuple(
        build_distribution(
            events,
            field=field,
            top_n=top_n,
            options=resolved_options,
        )
        for field in unique_fields
    )
