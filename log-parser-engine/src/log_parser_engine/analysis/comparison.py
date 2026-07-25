"""Deterministic comparison of two immutable event snapshots."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from time import perf_counter

from log_parser_engine.exceptions.analysis import (
    AnalysisComparisonError,
    AnalysisEventLimitError,
    AnalysisGroupLimitError,
)
from log_parser_engine.models.analysis_insight import AnalysisInsight
from log_parser_engine.models.analysis_request import AnalysisRequest, ComparisonRequest
from log_parser_engine.models.analysis_summary import AnalysisSummary
from log_parser_engine.models.comparison_result import (
    ChangeDirection,
    ComparisonResult,
    GroupComparison,
    MetricComparison,
    MetricInterpretation,
)
from log_parser_engine.models.event_filter import EventFilter
from log_parser_engine.models.http_analysis import HTTPAnalysis
from log_parser_engine.models.latency_analysis import LatencyAnalysis
from log_parser_engine.models.stored_event import StoredEvent
from log_parser_engine.storage.query_engine import matches_event_filter

from .extractors import (
    get_event_type,
    get_host,
    get_http_path,
    get_http_status,
    get_parser_name,
    get_service,
)
from .helpers import bounded_dimension
from .http_analysis import analyze_http
from .latency import analyze_latency
from .options import AnalysisOptions
from .summary import summarize_events

GroupExtractor = Callable[[StoredEvent], str | None]

_LATENCY_METRICS = frozenset(
    {
        "average_duration_ms",
        "p50_duration_ms",
        "p95_duration_ms",
        "p99_duration_ms",
    }
)
_HTTP_METRICS = frozenset({"server_error_rate", "client_error_rate"})
_MINIMUM_SAMPLE_METRICS = _LATENCY_METRICS | _HTTP_METRICS | frozenset(
    {"error_rate", "critical_rate"}
)
_PERCENTILE_BY_METRIC = {
    "p50_duration_ms": 50.0,
    "p95_duration_ms": 95.0,
    "p99_duration_ms": 99.0,
}


@dataclass(frozen=True, slots=True)
class _ComparisonExecutionPlan:
    """Bounded analysis modules required by the requested comparison metrics."""

    needs_latency: bool
    needs_http: bool
    latency_percentiles: tuple[float, ...]
    normalize_throughput: bool


def _build_execution_plan(request: ComparisonRequest) -> _ComparisonExecutionPlan:
    requested = frozenset(request.metrics)
    requested_percentiles = tuple(
        percentile
        for metric, percentile in _PERCENTILE_BY_METRIC.items()
        if metric in requested
    )
    return _ComparisonExecutionPlan(
        needs_latency=bool(requested & _LATENCY_METRICS),
        needs_http=bool(requested & _HTTP_METRICS),
        latency_percentiles=requested_percentiles or (50.0,),
        normalize_throughput=request.normalize_by_time_span,
    )


def compare_event_snapshots(
    baseline_events: Sequence[StoredEvent],
    comparison_events: Sequence[StoredEvent],
    request: ComparisonRequest,
    *,
    options: AnalysisOptions | None = None,
) -> ComparisonResult:
    """Compare exact filtered snapshots without mutating or persisting data."""
    resolved_options = options or AnalysisOptions()
    _validate_comparison_inputs(
        baseline_events,
        comparison_events,
        request,
        resolved_options,
    )
    started = perf_counter()
    baseline = _apply_filter(baseline_events, request.baseline_filter)
    comparison = _apply_filter(comparison_events, request.comparison_filter)
    execution_plan = _build_execution_plan(request)

    baseline_summary = summarize_events(
        baseline,
        input_event_count=len(baseline_events),
        options=resolved_options,
    )
    comparison_summary = summarize_events(
        comparison,
        input_event_count=len(comparison_events),
        options=resolved_options,
    )
    analysis_request = (
        AnalysisRequest(
            include_summary=False,
            include_timeline=False,
            include_distributions=False,
            include_latency=execution_plan.needs_latency,
            include_http=execution_plan.needs_http,
            include_insights=False,
            percentiles=execution_plan.latency_percentiles,
        )
        if execution_plan.needs_latency or execution_plan.needs_http
        else None
    )
    baseline_latency = (
        analyze_latency(
            baseline,
            analysis_request,
            options=resolved_options,
        )
        if execution_plan.needs_latency and analysis_request is not None
        else None
    )
    comparison_latency = (
        analyze_latency(
            comparison,
            analysis_request,
            options=resolved_options,
        )
        if execution_plan.needs_latency and analysis_request is not None
        else None
    )
    baseline_http = (
        analyze_http(
            baseline,
            analysis_request,
            options=resolved_options,
        )
        if execution_plan.needs_http and analysis_request is not None
        else None
    )
    comparison_http = (
        analyze_http(
            comparison,
            analysis_request,
            options=resolved_options,
        )
        if execution_plan.needs_http and analysis_request is not None
        else None
    )

    threshold = (
        request.significant_change_percent
        if request.significant_change_percent is not None
        else resolved_options.significant_change_percent
    )
    metric_comparisons_list: list[MetricComparison] = []
    for metric in request.metrics:
        metric_comparisons_list.append(
            _compare_metric(
                metric,
                _metric_value(
                    metric,
                    summary=baseline_summary,
                    latency=baseline_latency,
                    http=baseline_http,
                    normalize_throughput=execution_plan.normalize_throughput,
                ),
                _metric_value(
                    metric,
                    summary=comparison_summary,
                    latency=comparison_latency,
                    http=comparison_http,
                    normalize_throughput=execution_plan.normalize_throughput,
                ),
                threshold=threshold,
                normalize_throughput=execution_plan.normalize_throughput,
                baseline_sample_count=_metric_sample_count(
                    metric,
                    summary=baseline_summary,
                    latency=baseline_latency,
                    http=baseline_http,
                ),
                comparison_sample_count=_metric_sample_count(
                    metric,
                    summary=comparison_summary,
                    latency=comparison_latency,
                    http=comparison_http,
                ),
                minimum_sample_count=resolved_options.minimum_comparison_count,
                require_minimum_samples=metric in _MINIMUM_SAMPLE_METRICS,
            )
        )
    metric_comparisons = tuple(metric_comparisons_list)
    group_comparisons = _compare_groups(
        baseline,
        comparison,
        request,
        threshold=threshold,
        options=resolved_options,
    )
    insights = _comparison_insights(metric_comparisons)
    warnings = _comparison_warnings(
        baseline_count=len(baseline),
        comparison_count=len(comparison),
        baseline_summary=baseline_summary,
        comparison_summary=comparison_summary,
        normalized_throughput=(
            "throughput" in request.metrics
            and execution_plan.normalize_throughput
        ),
        low_sample_size=(
            any(
                "LOW_SAMPLE_SIZE" in metric.notes
                for metric in metric_comparisons
            )
            or any(
                "LOW_SAMPLE_SIZE" in metric.notes
                for group in group_comparisons
                for metric in group.metric_comparisons
            )
        ),
    )
    return ComparisonResult(
        baseline_label=request.baseline_label,
        comparison_label=request.comparison_label,
        baseline_summary=baseline_summary,
        comparison_summary=comparison_summary,
        metric_comparisons=metric_comparisons,
        group_comparisons=group_comparisons,
        insights=insights,
        baseline_event_count=len(baseline),
        comparison_event_count=len(comparison),
        duration_ms=(perf_counter() - started) * 1000.0,
        warnings=warnings,
        metadata=request.metadata,
    )


def _validate_comparison_inputs(
    baseline: Sequence[StoredEvent],
    comparison: Sequence[StoredEvent],
    request: ComparisonRequest,
    options: AnalysisOptions,
) -> None:
    if not isinstance(request, ComparisonRequest):
        raise TypeError("request must be a ComparisonRequest")
    if request.top_n > options.max_top_n:
        raise AnalysisComparisonError(
            "comparison top_n exceeds the configured limit"
        )
    if len(request.group_by) > options.max_group_fields_per_request:
        raise AnalysisComparisonError(
            "comparison group count exceeds the configured limit"
        )
    if len(request.metrics) > options.max_comparison_metrics_per_request:
        raise AnalysisComparisonError(
            "comparison metric count exceeds the configured limit"
        )
    for events in (baseline, comparison):
        if isinstance(events, (str, bytes)) or not isinstance(events, Sequence):
            raise TypeError("comparison inputs must be StoredEvent sequences")
        if len(events) > options.max_events:
            raise AnalysisEventLimitError(len(events), options.max_events)
        if any(not isinstance(event, StoredEvent) for event in events):
            raise TypeError("comparison inputs must contain only StoredEvent")


def _apply_filter(
    events: Sequence[StoredEvent],
    event_filter: EventFilter | None,
) -> tuple[StoredEvent, ...]:
    if event_filter is None:
        return tuple(events)
    return tuple(event for event in events if matches_event_filter(event, event_filter))


def _metric_value(
    metric: str,
    *,
    summary: AnalysisSummary,
    latency: LatencyAnalysis | None,
    http: HTTPAnalysis | None,
    normalize_throughput: bool,
) -> float | None:
    values: dict[str, float | int | None] = {
        "event_count": summary.matched_event_count,
        "error_rate": summary.error_rate,
        "critical_rate": summary.critical_rate,
        "average_duration_ms": latency.mean_ms if latency is not None else None,
        "p50_duration_ms": (
            latency.percentiles.percentile_values.get(50.0)
            if latency is not None
            else None
        ),
        "p95_duration_ms": (
            latency.percentiles.percentile_values.get(95.0)
            if latency is not None
            else None
        ),
        "p99_duration_ms": (
            latency.percentiles.percentile_values.get(99.0)
            if latency is not None
            else None
        ),
        "server_error_rate": (
            http.server_error_rate if http is not None else None
        ),
        "client_error_rate": (
            http.client_error_rate if http is not None else None
        ),
        "throughput": (
            summary.events_per_minute
            if normalize_throughput
            else summary.matched_event_count
        ),
    }
    value = values.get(metric)
    return float(value) if value is not None else None


def _metric_sample_count(
    metric: str,
    *,
    summary: AnalysisSummary,
    latency: LatencyAnalysis | None,
    http: HTTPAnalysis | None,
) -> int:
    if metric in _LATENCY_METRICS:
        return latency.sample_count if latency is not None else 0
    if metric in _HTTP_METRICS:
        return http.http_event_count if http is not None else 0
    return summary.matched_event_count


def _compare_metric(
    metric: str,
    baseline: float | None,
    comparison: float | None,
    *,
    threshold: float,
    normalize_throughput: bool = True,
    baseline_sample_count: int | None = None,
    comparison_sample_count: int | None = None,
    minimum_sample_count: int = 0,
    require_minimum_samples: bool = False,
) -> MetricComparison:
    unit = _metric_unit(
        metric,
        normalize_throughput=normalize_throughput,
    )
    absolute: float | None = None
    percent: float | None = None
    percent_overflow = False
    direction: ChangeDirection = "undefined"
    if baseline is not None and comparison is not None:
        absolute = comparison - baseline
        if baseline == 0:
            if comparison == 0:
                percent = 0.0
                direction = "unchanged"
            else:
                direction = "new"
        else:
            try:
                calculated_percent = absolute / abs(baseline) * 100.0
            except OverflowError:
                calculated_percent = math.inf
            if math.isfinite(calculated_percent):
                percent = calculated_percent
            else:
                percent_overflow = True
            if absolute > 0:
                direction = "increase"
            elif absolute < 0:
                direction = "decrease"
            else:
                direction = "unchanged"
    elif baseline is None and comparison is not None:
        direction = "new"
    elif baseline is not None and comparison is None:
        direction = "removed"

    significant = (
        percent is not None and abs(percent) >= threshold
    ) or percent_overflow or direction in {"new", "removed"}
    interpretation = _interpretation(metric, direction)
    notes: list[str] = []
    if baseline == 0 and comparison not in {None, 0}:
        notes.append("baseline is zero; percent change is undefined")
    if percent_overflow:
        notes.append("percent change exceeds finite numeric range")
    if metric == "throughput":
        notes.append(
            "normalized by observed time span"
            if normalize_throughput
            else "time-span normalization disabled; raw event counts compared"
        )
    if require_minimum_samples and (
        baseline_sample_count is None
        or comparison_sample_count is None
        or baseline_sample_count < minimum_sample_count
        or comparison_sample_count < minimum_sample_count
    ):
        significant = False
        notes.append("LOW_SAMPLE_SIZE")
    return MetricComparison(
        metric=metric,
        unit=unit,
        baseline_value=baseline,
        comparison_value=comparison,
        absolute_change=absolute,
        percent_change=percent,
        direction=direction,
        significant=significant,
        interpretation=interpretation,
        notes=tuple(notes),
    )


def _metric_unit(
    metric: str,
    *,
    normalize_throughput: bool,
) -> str:
    if metric.endswith("_rate"):
        return "ratio"
    if metric.endswith("_ms"):
        return "ms"
    if metric == "throughput":
        return "events_per_minute" if normalize_throughput else "count"
    return "count"


def _interpretation(
    metric: str,
    direction: ChangeDirection,
) -> MetricInterpretation:
    if direction in {"undefined", "new", "removed"}:
        return "unknown"
    if metric in {
        "error_rate",
        "critical_rate",
        "average_duration_ms",
        "p50_duration_ms",
        "p95_duration_ms",
        "p99_duration_ms",
        "server_error_rate",
        "client_error_rate",
    }:
        if direction == "increase":
            return "degraded"
        if direction == "decrease":
            return "improved"
    return "neutral"


def _compare_groups(
    baseline: Sequence[StoredEvent],
    comparison: Sequence[StoredEvent],
    request: ComparisonRequest,
    *,
    threshold: float,
    options: AnalysisOptions,
) -> tuple[GroupComparison, ...]:
    results: list[GroupComparison] = []
    for field in request.group_by:
        extractor = _group_extractor(field, options)
        baseline_counts = _bounded_group_counts(
            baseline,
            extractor=extractor,
            field=field,
            options=options,
        )
        comparison_counts = _bounded_group_counts(
            comparison,
            extractor=extractor,
            field=field,
            options=options,
        )
        field_results: list[GroupComparison] = []
        for key in sorted(baseline_counts.keys() | comparison_counts.keys()):
            baseline_count = baseline_counts.get(key, 0)
            comparison_count = comparison_counts.get(key, 0)
            if max(baseline_count, comparison_count) < request.minimum_group_count:
                continue
            new_group = baseline_count == 0 and comparison_count > 0
            disappeared = baseline_count > 0 and comparison_count == 0
            if new_group and not request.include_new_groups:
                continue
            if disappeared and not request.include_disappeared_groups:
                continue
            baseline_percentage = (
                baseline_count / len(baseline) * 100.0 if baseline else 0.0
            )
            comparison_percentage = (
                comparison_count / len(comparison) * 100.0 if comparison else 0.0
            )
            count_comparison = _compare_metric(
                "event_count",
                float(baseline_count),
                float(comparison_count),
                threshold=threshold,
                normalize_throughput=False,
                baseline_sample_count=baseline_count,
                comparison_sample_count=comparison_count,
                minimum_sample_count=options.minimum_comparison_count,
                require_minimum_samples=True,
            )
            field_results.append(
                GroupComparison(
                    group_field=field,
                    key=key,
                    baseline_count=baseline_count,
                    comparison_count=comparison_count,
                    absolute_change=comparison_count - baseline_count,
                    percent_change=count_comparison.percent_change,
                    baseline_percentage=baseline_percentage,
                    comparison_percentage=comparison_percentage,
                    percentage_point_change=(
                        comparison_percentage - baseline_percentage
                    ),
                    new_group=new_group,
                    disappeared_group=disappeared,
                    significant=count_comparison.significant,
                    metric_comparisons=(count_comparison,),
                    attributes={},
                )
            )
        field_results.sort(
            key=lambda item: (
                -abs(item.percentage_point_change),
                -item.comparison_count,
                item.key,
            )
        )
        results.extend(field_results[: request.top_n])
    return tuple(results)


def _bounded_group_counts(
    events: Sequence[StoredEvent],
    *,
    extractor: GroupExtractor,
    field: str,
    options: AnalysisOptions,
) -> Counter[str]:
    counts: Counter[str] = Counter()
    for event in events:
        value = bounded_dimension(
            extractor(event),
            limit=options.max_dimension_value_length,
        )
        if value is None:
            continue
        if value not in counts and len(counts) >= options.max_groups:
            raise AnalysisGroupLimitError(
                field,
                len(counts) + 1,
                options.max_groups,
            )
        counts[value] += 1
    return counts


def _group_extractor(
    field: str,
    options: AnalysisOptions,
) -> GroupExtractor:
    extractors: dict[str, GroupExtractor] = {
        "severity": lambda event: event.event.severity.value,
        "event_type": get_event_type,
        "service": get_service,
        "host": get_host,
        "parser": get_parser_name,
        "parser_name": get_parser_name,
        "endpoint": lambda event: get_http_path(
            event,
            candidates=options.http_path_field_candidates,
            normalize_trailing_slash=options.normalize_endpoint_trailing_slash,
        ),
        "status_code": lambda event: (
            str(status)
            if (
                status := get_http_status(
                    event,
                    candidates=options.http_status_field_candidates,
                )
            )
            is not None
            else None
        ),
        "http_status": lambda event: (
            str(status)
            if (
                status := get_http_status(
                    event,
                    candidates=options.http_status_field_candidates,
                )
            )
            is not None
            else None
        ),
    }
    try:
        return extractors[field]
    except KeyError as exc:
        raise AnalysisComparisonError(
            f"unsupported comparison group field {field!r}"
        ) from exc


def _comparison_insights(
    metrics: tuple[MetricComparison, ...],
) -> tuple[AnalysisInsight, ...]:
    by_name = {metric.metric: metric for metric in metrics}
    insights: list[AnalysisInsight] = []
    error_rate = by_name.get("error_rate")
    if (
        error_rate is not None
        and error_rate.significant
        and error_rate.direction in {"increase", "new"}
    ):
        insights.append(
            AnalysisInsight(
                code="ERROR_SPIKE",
                level="warning",
                title="Error rate increased",
                message=(
                    "Hata oranı karşılaştırma döneminde yükselmiştir. "
                    "İlgili servis ve event türlerinin incelenmesi önerilir."
                ),
                metric="error_rate",
                current_value=error_rate.comparison_value,
                reference_value=error_rate.baseline_value,
                unit="ratio",
                evidence={"percent_change": error_rate.percent_change},
                recommendations=(
                    "Hata dağılımlarını servis ve event türü bazında inceleyin.",
                ),
            )
        )
    server_rate = by_name.get("server_error_rate")
    if (
        server_rate is not None
        and server_rate.significant
        and server_rate.direction in {"increase", "new"}
    ):
        insights.append(
            AnalysisInsight(
                code="SERVER_ERROR_SPIKE",
                level="warning",
                title="Server error rate increased",
                message=(
                    "5xx oranı önceki döneme göre yükselmiştir. "
                    "İlgili endpoint ve servislerin incelenmesi önerilir."
                ),
                metric="server_error_rate",
                current_value=server_rate.comparison_value,
                reference_value=server_rate.baseline_value,
                unit="ratio",
                evidence={"percent_change": server_rate.percent_change},
                recommendations=("5xx üreten endpointleri karşılaştırın.",),
            )
        )
    level_order = {"critical": 0, "warning": 1, "info": 2}
    return tuple(
        sorted(insights, key=lambda item: (level_order[item.level], item.code))
    )


def _comparison_warnings(
    *,
    baseline_count: int,
    comparison_count: int,
    baseline_summary: AnalysisSummary,
    comparison_summary: AnalysisSummary,
    normalized_throughput: bool,
    low_sample_size: bool,
) -> tuple[str, ...]:
    warnings: list[str] = []
    if baseline_count == 0:
        warnings.append("baseline dataset contains no matching events")
    if comparison_count == 0:
        warnings.append("comparison dataset contains no matching events")
    if normalized_throughput and baseline_summary.time_span_seconds == 0:
        warnings.append("baseline throughput is undefined for a zero time span")
    if normalized_throughput and comparison_summary.time_span_seconds == 0:
        warnings.append("comparison throughput is undefined for a zero time span")
    if low_sample_size:
        warnings.append("LOW_SAMPLE_SIZE")
    return tuple(warnings)
