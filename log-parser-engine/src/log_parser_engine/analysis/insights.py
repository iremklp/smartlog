from __future__ import annotations

from collections.abc import Sequence

from log_parser_engine.models.analysis_insight import AnalysisInsight, InsightLevel
from log_parser_engine.models.analysis_summary import AnalysisSummary
from log_parser_engine.models.distribution import DistributionResult
from log_parser_engine.models.http_analysis import HTTPAnalysis
from log_parser_engine.models.latency_analysis import LatencyAnalysis
from log_parser_engine.models.timeline import TimelineResult

from .options import AnalysisOptions

_LEVEL_ORDER = {"critical": 0, "warning": 1, "info": 2}


def _error_rate_insight(
    summary: AnalysisSummary,
    options: AnalysisOptions,
) -> AnalysisInsight | None:
    if summary.error_rate >= options.error_rate_critical_threshold:
        level: InsightLevel = "critical"
    elif summary.error_rate >= options.error_rate_warning_threshold:
        level = "warning"
    else:
        return None
    return AnalysisInsight(
        code="HIGH_ERROR_RATE",
        level=level,
        title="High error rate",
        message=(
            "Error and critical events exceed the configured threshold. "
            "Affected services and event types can be reviewed."
        ),
        metric="error_rate",
        current_value=summary.error_rate,
        reference_value=(
            options.error_rate_critical_threshold
            if level == "critical"
            else options.error_rate_warning_threshold
        ),
        unit="ratio",
        evidence={
            "error_count": summary.error_count,
            "critical_count": summary.critical_count,
            "event_count": summary.matched_event_count,
        },
        recommendations=(
            "Review the leading error event types and services.",
        ),
    )


def _critical_rate_insight(
    summary: AnalysisSummary,
    options: AnalysisOptions,
) -> AnalysisInsight | None:
    if summary.critical_count == 0:
        return None
    threshold = options.error_rate_warning_threshold
    if summary.critical_rate < threshold:
        return None
    level: InsightLevel = (
        "critical"
        if summary.critical_rate >= options.error_rate_critical_threshold
        else "warning"
    )
    return AnalysisInsight(
        code="HIGH_CRITICAL_RATE",
        level=level,
        title="Elevated critical-event rate",
        message=(
            "Critical events exceed the configured threshold. "
            "The corresponding sources can be investigated."
        ),
        metric="critical_rate",
        current_value=summary.critical_rate,
        reference_value=threshold,
        unit="ratio",
        evidence={
            "critical_count": summary.critical_count,
            "event_count": summary.matched_event_count,
        },
        recommendations=("Review critical events by service and host.",),
    )


def _dominance_insights(
    distributions: Sequence[DistributionResult],
    *,
    summary: AnalysisSummary,
    options: AnalysisOptions,
) -> list[AnalysisInsight]:
    if summary.matched_event_count < options.minimum_comparison_count:
        return []
    supported = {
        "service": (
            "SINGLE_SERVICE_CONCENTRATION",
            "Service concentration",
        ),
        "host": (
            "SINGLE_HOST_CONCENTRATION",
            "Host concentration",
        ),
        "event_type": (
            "DOMINANT_EVENT_TYPE",
            "Dominant event type",
        ),
    }
    result: list[AnalysisInsight] = []
    for distribution in distributions:
        metadata = supported.get(distribution.field)
        if metadata is None or not distribution.items:
            continue
        item = distribution.items[0]
        if item.percentage < options.dominant_group_warning_percentage:
            continue
        level: InsightLevel = (
            "critical"
            if item.percentage
            >= options.dominant_group_critical_percentage
            else "warning"
        )
        result.append(
            AnalysisInsight(
                code=metadata[0],
                level=level,
                title=metadata[1],
                message=(
                    f"One {distribution.field} accounts for a large share "
                    "of the analyzed events. This concentration can be reviewed."
                ),
                metric=f"{distribution.field}_percentage",
                current_value=item.percentage,
                reference_value=options.dominant_group_warning_percentage,
                unit="percent",
                evidence={
                    "key": item.key,
                    "count": item.count,
                    "event_count": distribution.total_count,
                },
                recommendations=(
                    f"Review the leading {distribution.field} in context.",
                ),
            )
        )
    return result


def _latency_insight(
    latency: LatencyAnalysis | None,
    options: AnalysisOptions,
) -> AnalysisInsight | None:
    if latency is None or latency.sample_count == 0:
        return None
    p95 = latency.percentiles.percentile_values.get(95.0)
    if p95 is None:
        return None
    critical = options.latency_critical_percentile_ms
    warning = options.latency_warning_percentile_ms
    if critical is not None and p95 >= critical:
        level: InsightLevel = "critical"
        threshold = critical
    elif warning is not None and p95 >= warning:
        level = "warning"
        threshold = warning
    else:
        return None
    return AnalysisInsight(
        code="LATENCY_P95_HIGH",
        level=level,
        title="High p95 latency",
        message=(
            "The p95 duration exceeds the configured threshold. "
            "Slow endpoints and services can be reviewed."
        ),
        metric="p95_duration_ms",
        current_value=p95,
        reference_value=threshold,
        unit="ms",
        evidence={"sample_count": latency.sample_count},
        recommendations=("Review the slowest endpoints and services.",),
    )


def _http_insights(
    http: HTTPAnalysis | None,
    options: AnalysisOptions,
) -> list[AnalysisInsight]:
    if http is None or http.http_event_count == 0:
        return []
    result: list[AnalysisInsight] = []
    missing_ratio = http.unknown_status_count / http.http_event_count
    if missing_ratio > 0.5:
        result.append(
            AnalysisInsight(
                code="MISSING_HTTP_STATUS_DATA",
                level="warning",
                title="HTTP status coverage is low",
                message=(
                    "More than half of HTTP events have no valid status code. "
                    "Parser mappings and source fields can be reviewed."
                ),
                metric="missing_http_status_rate",
                current_value=missing_ratio,
                reference_value=0.5,
                unit="ratio",
                evidence={
                    "missing_count": http.unknown_status_count,
                    "http_event_count": http.http_event_count,
                },
                recommendations=("Review HTTP status field mappings.",),
            )
        )
    if http.server_error_rate >= options.error_rate_warning_threshold:
        level: InsightLevel = (
            "critical"
            if http.server_error_rate
            >= options.error_rate_critical_threshold
            else "warning"
        )
        result.append(
            AnalysisInsight(
                code="HIGH_SERVER_ERROR_RATE",
                level=level,
                title="Elevated server-error rate",
                message=(
                    "The HTTP 5xx rate exceeds the configured threshold. "
                    "Related endpoints and services can be reviewed."
                ),
                metric="server_error_rate",
                current_value=http.server_error_rate,
                reference_value=(
                    options.error_rate_critical_threshold
                    if level == "critical"
                    else options.error_rate_warning_threshold
                ),
                unit="ratio",
                evidence={
                    "server_error_count": http.server_error_count,
                    "http_event_count": http.http_event_count,
                },
                recommendations=("Review endpoints with the highest 5xx counts.",),
            )
        )
    return result


def generate_insights(
    *,
    summary: AnalysisSummary,
    distributions: Sequence[DistributionResult] = (),
    latency: LatencyAnalysis | None = None,
    http: HTTPAnalysis | None = None,
    timeline: TimelineResult | None = None,
    options: AnalysisOptions | None = None,
) -> tuple[AnalysisInsight, ...]:
    """Generate bounded, cautious, deterministic rule-based observations."""
    resolved_options = options or AnalysisOptions()
    insights: list[AnalysisInsight] = []
    if summary.matched_event_count == 0:
        insights.append(
            AnalysisInsight(
                code="NO_EVENTS",
                level="info",
                title="No matching events",
                message="No events matched the requested analysis scope.",
                metric="event_count",
                current_value=0,
                unit="count",
                evidence={},
                recommendations=("Review the selected filters and time range.",),
            )
        )
    elif summary.matched_event_count < resolved_options.minimum_comparison_count:
        insights.append(
            AnalysisInsight(
                code="LOW_SAMPLE_SIZE",
                level="info",
                title="Low sample size",
                message=(
                    "The analysis contains a small number of events; "
                    "rates and rankings should be interpreted cautiously."
                ),
                metric="event_count",
                current_value=summary.matched_event_count,
                reference_value=resolved_options.minimum_comparison_count,
                unit="count",
                evidence={},
                recommendations=("Use a wider time range when appropriate.",),
            )
        )

    for candidate in (
        _error_rate_insight(summary, resolved_options),
        _critical_rate_insight(summary, resolved_options),
        _latency_insight(latency, resolved_options),
    ):
        if candidate is not None:
            insights.append(candidate)
    insights.extend(
        _dominance_insights(
            distributions,
            summary=summary,
            options=resolved_options,
        )
    )
    insights.extend(_http_insights(http, resolved_options))

    if (
        summary.matched_event_count
        and summary.events_with_duration / summary.matched_event_count < 0.2
    ):
        insights.append(
            AnalysisInsight(
                code="MISSING_DURATION_DATA",
                level="warning",
                title="Duration coverage is low",
                message=(
                    "Most analyzed events have no valid duration value. "
                    "Latency statistics may not represent the full dataset."
                ),
                metric="duration_coverage",
                current_value=(
                    summary.events_with_duration / summary.matched_event_count
                ),
                reference_value=0.2,
                unit="ratio",
                evidence={
                    "duration_event_count": summary.events_with_duration,
                    "event_count": summary.matched_event_count,
                },
                recommendations=("Review duration field mappings.",),
            )
        )
    if summary.out_of_order_timestamp_count:
        insights.append(
            AnalysisInsight(
                code="OUT_OF_ORDER_TIMESTAMPS",
                level="warning",
                title="Out-of-order event timestamps",
                message=(
                    "Some event timestamps are not ordered by insertion sequence. "
                    "Source clock differences or merged log streams can be reviewed."
                ),
                metric="out_of_order_timestamp_count",
                current_value=summary.out_of_order_timestamp_count,
                unit="count",
                evidence={
                    "event_count": summary.matched_event_count,
                },
                recommendations=("Review source timestamps and ingestion ordering.",),
            )
        )
    if timeline is not None and "TIME_BUCKET_ADJUSTED" in timeline.warnings:
        insights.append(
            AnalysisInsight(
                code="TIME_BUCKET_ADJUSTED",
                level="info",
                title="Timeline bucket adjusted",
                message=(
                    "The timeline bucket width was increased to remain within "
                    "the configured result limit."
                ),
                metric="bucket_seconds",
                current_value=timeline.bucket_seconds,
                unit="seconds",
                evidence={"bucket_count": len(timeline.buckets)},
                recommendations=(),
            )
        )

    unique = {insight.code: insight for insight in insights}
    return tuple(
        sorted(
            unique.values(),
            key=lambda insight: (_LEVEL_ORDER[insight.level], insight.code),
        )
    )
