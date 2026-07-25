"""Cross-model invariants for immutable statistical analysis results."""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from log_parser_engine.models import (
    AnalysisInsight,
    AnalysisRequest,
    AnalysisResult,
    AnalysisSummary,
    ComparisonResult,
    DistributionResult,
    HTTPAnalysis,
    LatencyAnalysis,
    MetricComparison,
    PercentileSummary,
    RankedItem,
    TimelineBucket,
    TimelineResult,
)


def _empty_distribution(field: str) -> DistributionResult:
    return DistributionResult(
        field=field,
        total_count=0,
        matched_value_count=0,
        missing_count=0,
        unique_value_count=0,
    )


def _empty_summary() -> AnalysisSummary:
    return AnalysisSummary(input_event_count=0, matched_event_count=0)


def test_empty_summary_and_result_are_valid_and_immutable() -> None:
    summary = _empty_summary()
    result = AnalysisResult(
        request=AnalysisRequest(),
        input_event_count=0,
        matched_event_count=0,
        analysis_duration_ms=0,
        summary=summary,
    )

    assert summary.error_rate == 0
    assert result.generated_at.tzinfo is not None
    with pytest.raises(ValidationError):
        result.matched_event_count = 1  # type: ignore[misc]
    with pytest.raises(TypeError, match="mutation"):
        result.metadata["new"] = True


def test_summary_rejects_inconsistent_error_count() -> None:
    with pytest.raises(ValidationError, match="error_or_critical_count"):
        AnalysisSummary(
            input_event_count=2,
            matched_event_count=2,
            error_count=1,
            error_or_critical_count=0,
        )


def test_timeline_enforces_order_and_derived_counts() -> None:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    bucket = TimelineBucket(
        start=start,
        end=start + timedelta(minutes=5),
        event_count=2,
        error_count=1,
        error_rate=0.5,
    )
    timeline = TimelineResult(
        bucket_seconds=300,
        start=start,
        end=start + timedelta(minutes=5),
        buckets=(bucket,),
        max_bucket_event_count=2,
        average_bucket_event_count=2,
        peak_bucket_start=start,
    )

    assert timeline.empty_bucket_count == 0
    with pytest.raises(ValidationError, match="max_bucket_event_count"):
        TimelineResult(
            bucket_seconds=300,
            start=start,
            end=start + timedelta(minutes=5),
            buckets=(bucket,),
            max_bucket_event_count=1,
            average_bucket_event_count=2,
        )


def test_percentile_summary_rejects_non_finite_values() -> None:
    with pytest.raises(ValidationError, match="finite"):
        PercentileSummary(
            sample_count=1,
            minimum=1,
            maximum=1,
            mean=1,
            median=1,
            standard_deviation=0,
            percentile_values={95: float("nan")},
        )


def test_analysis_nested_mappings_are_immutable_and_json_serializable() -> None:
    percentiles = PercentileSummary(
        sample_count=1,
        minimum=1,
        maximum=1,
        mean=1,
        median=1,
        standard_deviation=0,
        percentile_values={95: 1},
    )
    ranked = RankedItem(
        rank=1,
        key="gateway",
        display_value="gateway",
        count=1,
        percentage=100,
        attributes={"nested": {"values": [1, 2]}},
    )
    insight = AnalysisInsight(
        code="SAFE_EVIDENCE",
        level="info",
        title="Safe evidence",
        message="Evidence remains immutable.",
        evidence={"nested": {"count": 1}},
    )

    with pytest.raises(TypeError, match="mutation"):
        percentiles.percentile_values[95] = 2
    with pytest.raises(TypeError, match="mutation"):
        ranked.attributes["nested"]["new"] = "value"
    with pytest.raises(TypeError, match="mutation"):
        insight.evidence["nested"]["count"] = 2

    assert '"95.0":1.0' in percentiles.model_dump_json()
    assert '"count":1' in insight.model_dump_json()


def test_empty_latency_and_http_analysis() -> None:
    percentiles = PercentileSummary(sample_count=0)
    latency = LatencyAnalysis(
        total_events=0,
        sample_count=0,
        missing_count=0,
        invalid_count=0,
        percentiles=percentiles,
    )
    distribution = _empty_distribution("http")
    http = HTTPAnalysis(
        http_event_count=0,
        events_with_status=0,
        events_with_method=0,
        events_with_path=0,
        status_class_distribution=distribution,
        status_code_distribution=distribution,
        method_distribution=distribution,
        endpoint_distribution=distribution,
    )

    assert latency.minimum_ms is None
    assert http.total_error_rate == 0


def test_comparison_result_requires_summary_counts() -> None:
    summary = _empty_summary()
    metric = MetricComparison(
        metric="error_rate",
        unit="ratio",
        baseline_value=0,
        comparison_value=0,
        absolute_change=0,
        percent_change=0,
        direction="unchanged",
        significant=False,
        interpretation="neutral",
    )
    result = ComparisonResult(
        baseline_label="Before",
        comparison_label="After",
        baseline_summary=summary,
        comparison_summary=summary,
        baseline_event_count=0,
        comparison_event_count=0,
        duration_ms=1,
        metric_comparisons=(metric,),
    )

    assert result.metric_comparisons == (metric,)
