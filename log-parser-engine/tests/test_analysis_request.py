"""Focused request model tests for statistical analysis."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from log_parser_engine.models import AnalysisRequest, ComparisonRequest


def test_analysis_request_defaults_and_normalization() -> None:
    request = AnalysisRequest(
        percentiles=(95, 50, 95),
        group_fields=("severity", " attributes.team ", "severity"),
    )

    assert request.percentiles == (95.0, 50.0)
    assert request.group_fields == ("severity", "attributes.team")
    assert request.include_samples is False


def test_analysis_request_requires_aware_ordered_time_bounds() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        AnalysisRequest(start_time=datetime(2026, 1, 1))

    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError, match="before end_time"):
        AnalysisRequest(start_time=now, end_time=now)


def test_analysis_request_bounds_timeline_bucket_size() -> None:
    with pytest.raises(ValidationError, match="less than or equal"):
        AnalysisRequest(time_bucket_seconds=10**20)


def test_analysis_request_rejects_unsafe_paths_and_percentiles() -> None:
    with pytest.raises(ValidationError, match="unsafe field path"):
        AnalysisRequest(group_fields=("attributes.__class__",))

    with pytest.raises(ValidationError, match="between 0 and 100"):
        AnalysisRequest(percentiles=(101,))


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("duration_field", "raw_message"),
        ("status_field", "message"),
        ("method_field", "raw_message"),
        ("path_field", "authorization.token"),
    ],
)
def test_analysis_request_rejects_sensitive_field_overrides(
    field_name: str,
    value: str,
) -> None:
    with pytest.raises(ValidationError, match="sensitive"):
        AnalysisRequest(**{field_name: value})


def test_analysis_request_rejects_sensitive_groups_and_unbounded_dimensions() -> None:
    with pytest.raises(ValidationError, match="sensitive"):
        AnalysisRequest(group_fields=("credentials.token",))

    with pytest.raises(ValidationError, match="more than 20"):
        AnalysisRequest(
            group_fields=tuple(f"attributes.field_{index}" for index in range(21))
        )

    with pytest.raises(ValidationError, match="more than 20"):
        AnalysisRequest(percentiles=tuple(float(index) for index in range(21)))


def test_analysis_request_requires_an_output_module() -> None:
    with pytest.raises(ValidationError, match="at least one include flag"):
        AnalysisRequest(
            include_summary=False,
            include_timeline=False,
            include_distributions=False,
            include_latency=False,
            include_http=False,
            include_insights=False,
            include_samples=False,
        )


def test_analysis_request_rejects_non_json_metadata() -> None:
    with pytest.raises(ValidationError, match="JSON-safe"):
        AnalysisRequest(metadata={"value": object()})


def test_analysis_request_metadata_is_deeply_immutable() -> None:
    request = AnalysisRequest(metadata={"nested": {"items": [1, 2]}})

    with pytest.raises(TypeError, match="mutation"):
        request.metadata["new"] = True
    with pytest.raises(TypeError, match="mutation"):
        request.metadata["nested"]["new"] = True
    assert request.metadata["nested"]["items"] == (1, 2)


def test_comparison_request_normalizes_and_validates_dimensions() -> None:
    request = ComparisonRequest(
        baseline_label=" Before ",
        comparison_label=" After ",
        metrics=("event_count", "event_count", "error_rate"),
        group_by=("service", "service"),
    )

    assert request.baseline_label == "Before"
    assert request.metrics == ("event_count", "error_rate")
    assert request.group_by == ("service",)

    with pytest.raises(ValidationError, match="unsupported comparison metric"):
        ComparisonRequest(metrics=("arbitrary_code",))
