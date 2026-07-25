from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime

from log_parser_engine.exceptions.analysis import (
    AnalysisGroupLimitError,
    AnalysisNumericValueError,
)
from log_parser_engine.models.analysis_request import AnalysisRequest
from log_parser_engine.models.distribution import DistributionResult
from log_parser_engine.models.http_analysis import (
    EndpointAnalysis,
    HTTPAnalysis,
    HTTPStatusBreakdown,
)
from log_parser_engine.models.stored_event import StoredEvent

from .extractors import (
    extract_duration_ms,
    get_http_method,
    get_http_path,
    get_http_status,
    get_service,
    http_status_class,
    is_http_event,
)
from .helpers import RunningStatistics, bounded_dimension, safe_ratio
from .options import AnalysisOptions
from .percentiles import calculate_percentile
from .ranking import ranked_items
from .sampling import BoundedDeterministicSample
from .timelines import build_timeline
from .validation import validate_stored_events


@dataclass(slots=True)
class _EndpointAccumulator:
    request_count: int = 0
    statuses: Counter[int] = field(default_factory=Counter)
    methods: set[str] = field(default_factory=set)
    services: set[str] = field(default_factory=set)
    duration_statistics: RunningStatistics = field(
        default_factory=RunningStatistics,
    )
    duration_samples: BoundedDeterministicSample[float] | None = field(
        default=None,
        repr=False,
    )
    client_errors: int = 0
    server_errors: int = 0
    first_seen: datetime | None = None
    last_seen: datetime | None = None


@dataclass(slots=True)
class _StatusAccumulator:
    total: int = 0
    informational: int = 0
    success: int = 0
    redirect: int = 0
    client_error: int = 0
    server_error: int = 0
    unknown: int = 0

    def add(self, status: int | None) -> None:
        self.total += 1
        status_class = http_status_class(status)
        if status_class == "1xx":
            self.informational += 1
        elif status_class == "2xx":
            self.success += 1
        elif status_class == "3xx":
            self.redirect += 1
        elif status_class == "4xx":
            self.client_error += 1
        elif status_class == "5xx":
            self.server_error += 1
        else:
            self.unknown += 1


def _ensure_group(
    groups: Mapping[str, object],
    key: str,
    *,
    field_name: str,
    options: AnalysisOptions,
) -> None:
    if key not in groups and len(groups) >= options.max_groups:
        raise AnalysisGroupLimitError(
            field_name,
            len(groups) + 1,
            options.max_groups,
        )


def _distribution_from_counts(
    *,
    field: str,
    counts: Counter[str],
    total_count: int,
    missing_count: int,
    top_n: int,
) -> DistributionResult:
    items, other_count, truncated = ranked_items(
        counts,
        total_count=total_count,
        top_n=top_n,
    )
    return DistributionResult(
        field=field,
        total_count=total_count,
        matched_value_count=sum(counts.values()),
        missing_count=missing_count,
        unique_value_count=len(counts),
        items=items,
        other_count=other_count,
        truncated=truncated,
    )


def _status_breakdown(
    key: str,
    accumulator: _StatusAccumulator,
) -> HTTPStatusBreakdown:
    return HTTPStatusBreakdown(
        key=key,
        total_count=accumulator.total,
        informational_count=accumulator.informational,
        success_count=accumulator.success,
        redirect_count=accumulator.redirect,
        client_error_count=accumulator.client_error,
        server_error_count=accumulator.server_error,
        unknown_status_count=accumulator.unknown,
        error_rate=safe_ratio(
            accumulator.client_error + accumulator.server_error,
            accumulator.total,
        ),
    )


def _endpoint_result(
    endpoint: str,
    accumulator: _EndpointAccumulator,
    *,
    http_event_count: int,
    top_n: int,
    options: AnalysisOptions,
) -> EndpointAnalysis:
    request_count = accumulator.request_count
    error_count = accumulator.client_errors + accumulator.server_errors
    duration_samples = (
        accumulator.duration_samples.values()
        if accumulator.duration_samples is not None
        else ()
    )
    duration_statistics = accumulator.duration_statistics
    status_counts = Counter(
        {str(status): count for status, count in accumulator.statuses.items()}
    )
    status_items, _, _ = ranked_items(
        status_counts,
        total_count=request_count,
        top_n=top_n,
    )
    return EndpointAnalysis(
        endpoint=endpoint,
        request_count=request_count,
        percentage=safe_ratio(request_count, http_event_count) * 100.0,
        error_count=error_count,
        error_rate=safe_ratio(error_count, request_count),
        client_error_count=accumulator.client_errors,
        server_error_count=accumulator.server_errors,
        latency_sample_count=duration_statistics.count,
        average_duration_ms=duration_statistics.mean,
        p95_duration_ms=(
            calculate_percentile(
                duration_samples,
                95,
                method=options.percentile_method,
            )
            if duration_samples
            else None
        ),
        max_duration_ms=duration_statistics.maximum,
        methods=tuple(sorted(accumulator.methods)),
        top_status_codes=status_items,
        services=tuple(sorted(accumulator.services)),
        first_seen=accumulator.first_seen,
        last_seen=accumulator.last_seen,
    )


def analyze_http(
    events: Sequence[StoredEvent],
    request: AnalysisRequest,
    *,
    options: AnalysisOptions | None = None,
) -> HTTPAnalysis:
    """Build deterministic HTTP status, method, endpoint, and latency analysis."""
    resolved_options = options or AnalysisOptions()
    validate_stored_events(events)
    top_n = request.top_n or resolved_options.default_top_n

    def matches_http(event: StoredEvent) -> bool:
        return is_http_event(
            event,
            status_field=request.status_field,
            method_field=request.method_field,
            path_field=request.path_field,
            status_candidates=resolved_options.http_status_field_candidates,
            method_candidates=resolved_options.http_method_field_candidates,
            path_candidates=resolved_options.http_path_field_candidates,
        )

    status_class_counts: Counter[str] = Counter()
    status_code_counts: Counter[str] = Counter()
    method_counts: Counter[str] = Counter()
    endpoint_counts: Counter[str] = Counter()
    endpoints: dict[str, _EndpointAccumulator] = {}
    by_method: dict[str, _StatusAccumulator] = {}
    by_service: dict[str, _StatusAccumulator] = {}
    informational = success = redirect = client_error = server_error = 0
    events_with_status = events_with_method = events_with_path = 0
    http_count = 0
    endpoint_samples_approximated = False

    for event in events:
        if not matches_http(event):
            continue
        http_count += 1
        status = get_http_status(
            event,
            explicit_field=request.status_field,
            candidates=resolved_options.http_status_field_candidates,
            max_depth=resolved_options.max_attribute_depth,
        )
        method = get_http_method(
            event,
            explicit_field=request.method_field,
            candidates=resolved_options.http_method_field_candidates,
            max_depth=resolved_options.max_attribute_depth,
        )
        endpoint = get_http_path(
            event,
            explicit_field=request.path_field,
            candidates=resolved_options.http_path_field_candidates,
            max_depth=resolved_options.max_attribute_depth,
            normalize_trailing_slash=(
                resolved_options.normalize_endpoint_trailing_slash
            ),
        )
        method = bounded_dimension(
            method,
            limit=resolved_options.max_dimension_value_length,
        )
        endpoint = bounded_dimension(
            endpoint,
            limit=resolved_options.max_dimension_value_length,
        )
        service = bounded_dimension(
            get_service(event),
            limit=resolved_options.max_dimension_value_length,
        )
        status_class = http_status_class(status)
        if status is not None:
            events_with_status += 1
            status_class_counts[status_class] += 1
            status_code_counts[str(status)] += 1
            if status_class == "1xx":
                informational += 1
            elif status_class == "2xx":
                success += 1
            elif status_class == "3xx":
                redirect += 1
            elif status_class == "4xx":
                client_error += 1
            elif status_class == "5xx":
                server_error += 1
        if method is not None:
            events_with_method += 1
            method_counts[method] += 1
            _ensure_group(
                by_method,
                method,
                field_name="http_method",
                options=resolved_options,
            )
            by_method.setdefault(method, _StatusAccumulator()).add(status)
        if service is not None:
            _ensure_group(
                by_service,
                service,
                field_name="service",
                options=resolved_options,
            )
            by_service.setdefault(service, _StatusAccumulator()).add(status)
        if endpoint is None:
            continue
        events_with_path += 1
        endpoint_counts[endpoint] += 1
        _ensure_group(
            endpoints,
            endpoint,
            field_name="endpoint",
            options=resolved_options,
        )
        accumulator = endpoints.setdefault(endpoint, _EndpointAccumulator())
        accumulator.request_count += 1
        accumulator.first_seen = (
            event.timestamp
            if accumulator.first_seen is None
            else min(accumulator.first_seen, event.timestamp)
        )
        accumulator.last_seen = (
            event.timestamp
            if accumulator.last_seen is None
            else max(accumulator.last_seen, event.timestamp)
        )
        if status is not None:
            accumulator.statuses[status] += 1
            if 400 <= status <= 499:
                accumulator.client_errors += 1
            elif 500 <= status <= 599:
                accumulator.server_errors += 1
        if method is not None:
            accumulator.methods.add(method)
        if service is not None:
            accumulator.services.add(service)
        duration = extract_duration_ms(
            event,
            explicit_field=request.duration_field,
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
        if duration.valid and duration.value is not None:
            if accumulator.duration_samples is None:
                accumulator.duration_samples = BoundedDeterministicSample(
                    max_samples=resolved_options.max_percentile_samples,
                    allow_sampling=resolved_options.allow_percentile_sampling,
                )
            accumulator.duration_samples.add(
                duration.value,
                key=f"{event.content_hash}:{event.id}:{event.sequence}",
            )
            accumulator.duration_statistics.add(duration.value)
            endpoint_samples_approximated = (
                endpoint_samples_approximated
                or accumulator.duration_samples.sampled
            )

    endpoint_results = tuple(
        _endpoint_result(
            endpoint,
            accumulator,
            http_event_count=http_count,
            top_n=top_n,
            options=resolved_options,
        )
        for endpoint, accumulator in endpoints.items()
    )
    slowest_endpoints = tuple(
        sorted(
            (
                item
                for item in endpoint_results
                if item.latency_sample_count
                >= resolved_options.minimum_endpoint_latency_samples
            ),
            key=lambda item: (
                -(item.p95_duration_ms or 0.0),
                -(item.average_duration_ms or 0.0),
                -item.request_count,
                item.endpoint,
            ),
        )[:top_n]
    )
    highest_error_endpoints = tuple(
        sorted(
            (
                item
                for item in endpoint_results
                if item.request_count
                >= resolved_options.minimum_endpoint_requests_for_rate
            ),
            key=lambda item: (
                -item.error_rate,
                -item.request_count,
                item.endpoint,
            ),
        )[:top_n]
    )
    warnings: list[str] = []
    unknown_status = http_count - events_with_status
    if http_count and unknown_status / http_count > 0.5:
        warnings.append("MISSING_HTTP_STATUS_DATA")
    if endpoint_samples_approximated:
        warnings.append("PERCENTILE_SAMPLED")

    return HTTPAnalysis(
        http_event_count=http_count,
        events_with_status=events_with_status,
        events_with_method=events_with_method,
        events_with_path=events_with_path,
        informational_count=informational,
        success_count=success,
        redirect_count=redirect,
        non_error_count=informational + success + redirect,
        client_error_count=client_error,
        server_error_count=server_error,
        unknown_status_count=unknown_status,
        success_rate=safe_ratio(success, http_count),
        non_error_rate=safe_ratio(
            informational + success + redirect,
            http_count,
        ),
        client_error_rate=safe_ratio(client_error, http_count),
        server_error_rate=safe_ratio(server_error, http_count),
        total_error_rate=safe_ratio(client_error + server_error, http_count),
        status_class_distribution=_distribution_from_counts(
            field="status_class",
            counts=status_class_counts,
            total_count=http_count,
            missing_count=unknown_status,
            top_n=top_n,
        ),
        status_code_distribution=_distribution_from_counts(
            field="http_status",
            counts=status_code_counts,
            total_count=http_count,
            missing_count=unknown_status,
            top_n=top_n,
        ),
        method_distribution=_distribution_from_counts(
            field="http_method",
            counts=method_counts,
            total_count=http_count,
            missing_count=http_count - events_with_method,
            top_n=top_n,
        ),
        endpoint_distribution=_distribution_from_counts(
            field="endpoint",
            counts=endpoint_counts,
            total_count=http_count,
            missing_count=http_count - events_with_path,
            top_n=top_n,
        ),
        slowest_endpoints=slowest_endpoints,
        highest_error_endpoints=highest_error_endpoints,
        status_by_method=tuple(
            _status_breakdown(key, accumulator)
            for key, accumulator in sorted(
                by_method.items(),
                key=lambda item: (-item[1].total, item[0]),
            )[:top_n]
        ),
        status_by_service=tuple(
            _status_breakdown(key, accumulator)
            for key, accumulator in sorted(
                by_service.items(),
                key=lambda item: (-item[1].total, item[0]),
            )[:top_n]
        ),
        timeline=(
            build_timeline(
                events,
                request,
                options=resolved_options,
                event_predicate=matches_http,
            )
            if request.include_timeline
            else None
        ),
        warnings=tuple(warnings),
    )
