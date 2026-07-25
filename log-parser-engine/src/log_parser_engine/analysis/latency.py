from __future__ import annotations

import statistics
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from log_parser_engine.exceptions.analysis import (
    AnalysisGroupLimitError,
    AnalysisNumericValueError,
)
from log_parser_engine.models.analysis_request import AnalysisRequest
from log_parser_engine.models.latency_analysis import (
    EndpointLatency,
    LatencyAnalysis,
    LatencyBucket,
    SlowEvent,
)
from log_parser_engine.models.percentile_summary import PercentileSummary
from log_parser_engine.models.stored_event import StoredEvent

from .extractors import (
    extract_duration_ms,
    get_event_type,
    get_host,
    get_http_path,
    get_message_preview,
    get_service,
)
from .helpers import RunningStatistics, bounded_dimension, safe_ratio
from .options import AnalysisOptions
from .percentiles import calculate_percentile, calculate_percentiles
from .sampling import BoundedDeterministicSample
from .validation import validate_stored_events

LATENCY_BUCKETS: tuple[tuple[float | None, float | None, str], ...] = (
    (None, 10.0, "<10 ms"),
    (10.0, 50.0, "10–50 ms"),
    (50.0, 100.0, "50–100 ms"),
    (100.0, 250.0, "100–250 ms"),
    (250.0, 500.0, "250–500 ms"),
    (500.0, 1_000.0, "500 ms–1 s"),
    (1_000.0, 2_000.0, "1–2 s"),
    (2_000.0, 5_000.0, "2–5 s"),
    (5_000.0, 10_000.0, "5–10 s"),
    (10_000.0, None, ">=10 s"),
)

GroupExtractor = Callable[[StoredEvent], str | None]


@dataclass(slots=True)
class _GroupAccumulator:
    statistics: RunningStatistics = field(default_factory=RunningStatistics)


def _latency_bucket_index(value: float) -> int:
    for index, (_, upper, _) in enumerate(LATENCY_BUCKETS):
        if upper is None or value < upper:
            return index
    return len(LATENCY_BUCKETS) - 1


def _build_buckets(
    counts: Sequence[int],
    *,
    total_count: int,
) -> tuple[LatencyBucket, ...]:
    return tuple(
        LatencyBucket(
            lower_bound_ms=lower,
            upper_bound_ms=upper,
            count=count,
            percentage=safe_ratio(count, total_count) * 100.0,
            label=label,
        )
        for (lower, upper, label), count in zip(LATENCY_BUCKETS, counts)
    )


def _add_group_value(
    groups: dict[str, _GroupAccumulator],
    key: str | None,
    value: float,
    *,
    field_name: str,
    options: AnalysisOptions,
) -> None:
    if key is None:
        return
    if key not in groups:
        if len(groups) >= options.max_groups:
            raise AnalysisGroupLimitError(
                field_name,
                len(groups) + 1,
                options.max_groups,
            )
        groups[key] = _GroupAccumulator()
    groups[key].statistics.add(value)


def _selected_group_keys(
    groups: dict[str, _GroupAccumulator],
    *,
    top_n: int,
) -> tuple[str, ...]:
    return tuple(
        key
        for key, _ in sorted(
            groups.items(),
            key=lambda item: (-item[1].statistics.count, item[0]),
        )[:top_n]
    )


def _group_latency(
    events: Sequence[StoredEvent],
    groups: dict[str, _GroupAccumulator],
    *,
    extractor: GroupExtractor,
    request: AnalysisRequest,
    top_n: int,
    options: AnalysisOptions,
) -> tuple[tuple[EndpointLatency, ...], bool]:
    """Build p95 samples only for selected groups, one dimension at a time."""
    selected = _selected_group_keys(groups, top_n=top_n)
    samples = {
        key: BoundedDeterministicSample[float](
            max_samples=options.max_percentile_samples,
            allow_sampling=options.allow_percentile_sampling,
        )
        for key in selected
    }
    for event in events:
        key = extractor(event)
        sample = samples.get(key) if key is not None else None
        if sample is None:
            continue
        extracted = extract_duration_ms(
            event,
            explicit_field=request.duration_field,
            candidates=options.duration_field_candidates,
            max_depth=options.max_attribute_depth,
            strict=options.strict_numeric_values,
        )
        if extracted.valid and extracted.value is not None:
            sample.add(
                extracted.value,
                key=f"{event.content_hash}:{event.id}:{event.sequence}",
            )

    result: list[EndpointLatency] = []
    sampled = False
    for key in selected:
        statistics = groups[key].statistics
        retained = samples[key].values()
        sampled = sampled or samples[key].sampled
        result.append(
            EndpointLatency(
                key=key,
                sample_count=statistics.count,
                minimum_ms=statistics.minimum,
                maximum_ms=statistics.maximum,
                mean_ms=statistics.mean,
                p95_ms=calculate_percentile(
                    retained,
                    95,
                    method=options.percentile_method,
                ),
            )
        )
    return tuple(result), sampled


def _slow_event_sort_key(
    item: tuple[StoredEvent, float],
) -> tuple[float, object, int, str]:
    event, value = item
    return (-value, event.timestamp, event.sequence, event.id)


def _retain_slowest(
    retained: list[tuple[StoredEvent, float]],
    item: tuple[StoredEvent, float],
    *,
    top_n: int,
) -> None:
    """Retain only the deterministic top-N slowest event references."""
    if len(retained) < top_n:
        retained.append(item)
        return
    worst_index = max(
        range(len(retained)),
        key=lambda index: _slow_event_sort_key(retained[index]),
    )
    if _slow_event_sort_key(item) < _slow_event_sort_key(retained[worst_index]):
        retained[worst_index] = item


def _percentile_summary(
    sample: BoundedDeterministicSample[float],
    running: RunningStatistics,
    *,
    request: AnalysisRequest,
    missing_count: int,
    invalid_count: int,
    options: AnalysisOptions,
) -> PercentileSummary:
    retained = sample.values()
    retained_summary = calculate_percentiles(
        retained,
        request.percentiles,
        method=options.percentile_method,
    )
    return PercentileSummary(
        sample_count=running.count,
        minimum=running.minimum,
        maximum=running.maximum,
        mean=running.mean,
        median=statistics.median(retained) if retained else None,
        standard_deviation=running.population_standard_deviation,
        percentile_values=retained_summary.percentile_values,
        missing_count=missing_count,
        invalid_count=invalid_count,
        percentile_sample_count=len(retained),
        percentiles_approximated=sample.sampled,
    )


def analyze_latency(
    events: Sequence[StoredEvent],
    request: AnalysisRequest,
    *,
    options: AnalysisOptions | None = None,
) -> LatencyAnalysis:
    """Analyze latency with bounded samples and exact streaming counters."""
    resolved_options = options or AnalysisOptions()
    validate_stored_events(events)
    top_n = request.top_n or resolved_options.default_top_n

    statistics = RunningStatistics()
    percentile_sample = BoundedDeterministicSample[float](
        max_samples=resolved_options.max_percentile_samples,
        allow_sampling=resolved_options.allow_percentile_sampling,
    )
    bucket_counts = [0] * len(LATENCY_BUCKETS)
    slowest_candidates: list[tuple[StoredEvent, float]] = []
    field_counts: Counter[str] = Counter()
    missing_count = 0
    invalid_count = 0
    per_service: dict[str, _GroupAccumulator] = {}
    per_event_type: dict[str, _GroupAccumulator] = {}
    per_endpoint: dict[str, _GroupAccumulator] = {}

    def endpoint(event: StoredEvent) -> str | None:
        return bounded_dimension(
            get_http_path(
                event,
                explicit_field=request.path_field,
                candidates=resolved_options.http_path_field_candidates,
                max_depth=resolved_options.max_attribute_depth,
                normalize_trailing_slash=(
                    resolved_options.normalize_endpoint_trailing_slash
                ),
            ),
            limit=resolved_options.max_dimension_value_length,
        )

    def service(event: StoredEvent) -> str | None:
        return bounded_dimension(
            get_service(event),
            limit=resolved_options.max_dimension_value_length,
        )

    def event_type(event: StoredEvent) -> str | None:
        return bounded_dimension(
            get_event_type(event),
            limit=resolved_options.max_dimension_value_length,
        )

    dimensions: tuple[
        tuple[str, dict[str, _GroupAccumulator], GroupExtractor],
        ...,
    ] = (
        ("service", per_service, service),
        ("event_type", per_event_type, event_type),
        ("endpoint", per_endpoint, endpoint),
    )

    for event in events:
        extracted = extract_duration_ms(
            event,
            explicit_field=request.duration_field,
            candidates=resolved_options.duration_field_candidates,
            max_depth=resolved_options.max_attribute_depth,
            strict=resolved_options.strict_numeric_values,
        )
        if not extracted.found:
            missing_count += 1
            continue
        if not extracted.valid or extracted.value is None:
            if not resolved_options.ignore_non_finite_values:
                raise AnalysisNumericValueError(
                    "duration field contains an invalid numeric value"
                )
            invalid_count += 1
            continue

        value = extracted.value
        sample_key = f"{event.content_hash}:{event.id}:{event.sequence}"
        percentile_sample.add(value, key=sample_key)
        statistics.add(value)
        bucket_counts[_latency_bucket_index(value)] += 1
        _retain_slowest(
            slowest_candidates,
            (event, value),
            top_n=top_n,
        )
        if extracted.field is not None:
            field_counts[extracted.field] += 1
        for field_name, groups, extractor in dimensions:
            _add_group_value(
                groups,
                extractor(event),
                value,
                field_name=field_name,
                options=resolved_options,
            )

    percentile_summary = _percentile_summary(
        percentile_sample,
        statistics,
        request=request,
        missing_count=missing_count,
        invalid_count=invalid_count,
        options=resolved_options,
    )
    warnings: list[str] = []
    if percentile_summary.percentiles_approximated:
        warnings.append("PERCENTILE_SAMPLED")

    detected_field = None
    if field_counts:
        candidate_order = {
            field: index
            for index, field in enumerate(
                (
                    *((request.duration_field,) if request.duration_field else ()),
                    *resolved_options.duration_field_candidates,
                )
            )
        }
        detected_field = min(
            field_counts,
            key=lambda field: (
                -field_counts[field],
                candidate_order.get(field, len(candidate_order)),
                field,
            ),
        )

    slowest = tuple(
        SlowEvent(
            event_id=event.id,
            timestamp=event.timestamp,
            duration_ms=value,
            event_type=event_type(event),
            service=service(event),
            host=bounded_dimension(
                get_host(event),
                limit=resolved_options.max_dimension_value_length,
            ),
            path=endpoint(event),
            message_preview=get_message_preview(event),
        )
        for event, value in sorted(
            slowest_candidates,
            key=_slow_event_sort_key,
        )
    )
    grouped_results: list[tuple[EndpointLatency, ...]] = []
    for _, groups, extractor in dimensions:
        result, sampled = _group_latency(
            events,
            groups,
            extractor=extractor,
            request=request,
            top_n=top_n,
            options=resolved_options,
        )
        grouped_results.append(result)
        if sampled:
            warnings.append("PERCENTILE_SAMPLED")

    return LatencyAnalysis(
        detected_field=detected_field,
        unit="ms",
        total_events=len(events),
        sample_count=statistics.count,
        missing_count=missing_count,
        invalid_count=invalid_count,
        minimum_ms=percentile_summary.minimum,
        maximum_ms=percentile_summary.maximum,
        mean_ms=percentile_summary.mean,
        median_ms=percentile_summary.median,
        standard_deviation_ms=percentile_summary.standard_deviation,
        percentiles=percentile_summary,
        slowest_events=slowest,
        latency_buckets=_build_buckets(
            bucket_counts,
            total_count=statistics.count,
        ),
        per_service=grouped_results[0],
        per_event_type=grouped_results[1],
        per_endpoint=grouped_results[2],
        warnings=tuple(dict.fromkeys(warnings)),
    )
