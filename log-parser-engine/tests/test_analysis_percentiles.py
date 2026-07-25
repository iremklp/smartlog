from __future__ import annotations

import math
import statistics

import pytest

from log_parser_engine.analysis.percentiles import (
    calculate_percentile,
    calculate_percentiles,
)
from log_parser_engine.exceptions.analysis import (
    AnalysisNumericValueError,
    AnalysisSampleLimitError,
)


def test_empty_and_single_sample() -> None:
    empty = calculate_percentiles([], (0, 50, 100))
    assert empty.sample_count == 0
    assert empty.percentile_values == {0.0: None, 50.0: None, 100.0: None}

    single = calculate_percentiles([7], (0, 50, 100))
    assert single.percentile_values == {0.0: 7, 50.0: 7, 100.0: 7}
    assert single.standard_deviation == 0


def test_nearest_rank_percentiles() -> None:
    values = [4, 1, 3, 2]
    assert calculate_percentile(values, 0) == 1
    assert calculate_percentile(values, 50) == 2
    assert calculate_percentile(values, 95) == 4
    assert calculate_percentile(values, 100) == 4
    assert values == [4, 1, 3, 2]


def test_linear_percentiles_for_even_and_odd_samples() -> None:
    assert calculate_percentile([0, 10], 50, method="linear") == 5
    assert calculate_percentile([0, 10, 20], 25, method="linear") == 5
    assert calculate_percentile([0, 10, 20], 50, method="linear") == 10


def test_duplicate_percentiles_are_removed() -> None:
    result = calculate_percentiles([1, 2, 3], (50, 50.0, 95))
    assert tuple(result.percentile_values) == (50.0, 95.0)


def test_population_standard_deviation() -> None:
    result = calculate_percentiles([1, 2, 3], (50,))
    assert result.mean == 2
    assert result.median == 2
    assert result.standard_deviation == pytest.approx(math.sqrt(2 / 3))


def test_invalid_samples_can_be_ignored_or_rejected() -> None:
    result = calculate_percentiles(
        [1, -1, float("nan"), float("inf"), 3],
        (50,),
    )
    assert result.sample_count == 2
    assert result.invalid_count == 3
    assert result.percentile_values[50.0] == 1
    with pytest.raises(AnalysisNumericValueError):
        calculate_percentiles(
            [1, float("nan")],
            (50,),
            ignore_invalid=False,
        )


def test_exact_sample_limit_and_explicit_deterministic_sampling() -> None:
    values = list(range(10))
    with pytest.raises(AnalysisSampleLimitError):
        calculate_percentiles(values, (50,), max_samples=3)
    sampled = calculate_percentiles(
        values,
        (0, 50, 100),
        max_samples=3,
        allow_sampling=True,
    )
    assert sampled.sample_count == 10
    assert sampled.percentile_sample_count == 3
    assert sampled.percentiles_approximated is True
    assert sampled.minimum == 0
    assert sampled.maximum == 9
    assert sampled.mean == 4.5
    assert sampled.median == 4.5
    assert sampled.percentile_values == {0.0: 0, 50.0: 3, 100.0: 6}


def test_sampling_preserves_full_dataset_descriptive_statistics() -> None:
    values = list(range(100))

    result = calculate_percentiles(
        values,
        (50, 95, 99),
        max_samples=10,
        allow_sampling=True,
    )

    assert result.sample_count == 100
    assert result.percentile_sample_count == 10
    assert result.percentiles_approximated is True
    assert result.minimum == 0
    assert result.maximum == 99
    assert result.mean == 49.5
    assert result.median == 49.5
    assert result.standard_deviation == pytest.approx(
        statistics.pstdev(values)
    )


@pytest.mark.parametrize("percentile", [-1, 101, float("nan")])
def test_invalid_percentile_is_rejected(percentile: float) -> None:
    with pytest.raises(ValueError):
        calculate_percentile([1], percentile)
