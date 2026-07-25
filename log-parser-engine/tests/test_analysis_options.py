"""Focused validation tests for statistical analysis configuration."""

import pytest
from pydantic import ValidationError

from log_parser_engine.analysis.options import AnalysisOptions


def test_analysis_options_defaults_are_bounded_and_immutable() -> None:
    options = AnalysisOptions()

    assert options.max_events == 1_000_000
    assert options.default_top_n <= options.max_top_n
    assert options.percentile_method == "nearest_rank"

    with pytest.raises(ValidationError):
        options.max_events = 1  # type: ignore[misc]


def test_analysis_options_normalize_candidate_paths() -> None:
    options = AnalysisOptions(
        duration_field_candidates=(" duration_ms ", "duration_ms", "latency_ms")
    )

    assert options.duration_field_candidates == ("duration_ms", "latency_ms")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_events", 0),
        ("max_groups", -1),
        ("max_timeline_buckets", 0),
        ("max_attribute_depth", 21),
    ],
)
def test_analysis_options_reject_invalid_limits(
    field: str,
    value: int,
) -> None:
    with pytest.raises(ValidationError):
        AnalysisOptions(**{field: value})


def test_analysis_options_reject_invalid_threshold_order() -> None:
    with pytest.raises(ValidationError, match="thresholds"):
        AnalysisOptions(
            error_rate_warning_threshold=0.5,
            error_rate_critical_threshold=0.2,
        )

    with pytest.raises(ValidationError, match="latency warning"):
        AnalysisOptions(
            latency_warning_percentile_ms=500,
            latency_critical_percentile_ms=100,
        )

    with pytest.raises(ValidationError, match="dominant group"):
        AnalysisOptions(
            dominant_group_warning_percentage=90,
            dominant_group_critical_percentage=80,
        )


@pytest.mark.parametrize(
    "field",
    [
        "significant_change_percent",
        "latency_warning_percentile_ms",
        "dominant_group_warning_percentage",
    ],
)
def test_analysis_options_reject_non_finite_thresholds(field: str) -> None:
    with pytest.raises(ValidationError, match="finite"):
        AnalysisOptions(**{field: float("nan")})
