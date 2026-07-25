from __future__ import annotations

import math
import statistics
from collections.abc import Sequence
from decimal import Decimal

from log_parser_engine.exceptions.analysis import (
    AnalysisNumericValueError,
    AnalysisSampleLimitError,
)
from log_parser_engine.models.percentile_summary import PercentileSummary

from .sampling import deterministic_sample


def _clean_values(
    values: Sequence[float | int | Decimal],
    *,
    ignore_invalid: bool,
    reject_negative: bool,
) -> tuple[list[float], int]:
    cleaned: list[float] = []
    invalid_count = 0
    for value in values:
        if isinstance(value, bool):
            converted = math.nan
        else:
            try:
                converted = float(value)
            except (TypeError, ValueError, OverflowError):
                converted = math.nan
        if not math.isfinite(converted) or (reject_negative and converted < 0):
            invalid_count += 1
            if not ignore_invalid:
                raise AnalysisNumericValueError(
                    "numeric samples contain an invalid value"
                )
            continue
        cleaned.append(converted)
    return cleaned, invalid_count


def _validate_percentile(percentile: float) -> float:
    value = float(percentile)
    if not math.isfinite(value) or not 0.0 <= value <= 100.0:
        raise ValueError("percentile must be between 0 and 100")
    return value


def _percentile_from_sorted(
    values: Sequence[float],
    percentile: float,
    *,
    method: str,
) -> float | None:
    if not values:
        return None
    if method == "nearest_rank":
        if percentile == 0:
            return values[0]
        rank = math.ceil((percentile / 100.0) * len(values))
        return values[max(0, rank - 1)]
    if method == "linear":
        if len(values) == 1:
            return values[0]
        position = (percentile / 100.0) * (len(values) - 1)
        lower_index = math.floor(position)
        upper_index = math.ceil(position)
        if lower_index == upper_index:
            return values[lower_index]
        fraction = position - lower_index
        return values[lower_index] + (
            values[upper_index] - values[lower_index]
        ) * fraction
    raise ValueError("method must be 'nearest_rank' or 'linear'")


def calculate_percentile(
    values: Sequence[float | int | Decimal],
    percentile: float,
    *,
    method: str = "nearest_rank",
    ignore_invalid: bool = True,
    reject_negative: bool = True,
) -> float | None:
    """Calculate an exact percentile from a sorted copy of numeric samples."""
    requested = _validate_percentile(percentile)
    cleaned, _ = _clean_values(
        values,
        ignore_invalid=ignore_invalid,
        reject_negative=reject_negative,
    )
    cleaned.sort()
    return _percentile_from_sorted(cleaned, requested, method=method)


def calculate_percentiles(
    values: Sequence[float | int | Decimal],
    percentiles: Sequence[float],
    *,
    method: str = "nearest_rank",
    missing_count: int = 0,
    invalid_count: int = 0,
    ignore_invalid: bool = True,
    reject_negative: bool = True,
    max_samples: int | None = None,
    allow_sampling: bool = False,
) -> PercentileSummary:
    """Return exact descriptive statistics and requested percentile values.

    When explicit sampling is enabled here, only requested percentile values
    are approximated. Count, extrema, mean, median, and population standard
    deviation continue to describe every valid input value. Streaming callers
    that retain only a bounded sample, such as latency analysis, calculate both
    median and requested percentiles from that retained sample and mark the
    result as approximated.
    """
    if missing_count < 0 or invalid_count < 0:
        raise ValueError("missing_count and invalid_count must not be negative")
    requested = tuple(dict.fromkeys(_validate_percentile(item) for item in percentiles))
    cleaned, discovered_invalid = _clean_values(
        values,
        ignore_invalid=ignore_invalid,
        reject_negative=reject_negative,
    )
    total_invalid = invalid_count + discovered_invalid
    sample_count = len(cleaned)
    percentile_values_source = cleaned
    percentiles_approximated = False
    if max_samples is not None:
        if max_samples <= 0:
            raise ValueError("max_samples must be positive")
        if sample_count > max_samples:
            if not allow_sampling:
                raise AnalysisSampleLimitError(
                    f"numeric sample count {sample_count} exceeds limit {max_samples}"
                )
            percentile_values_source = list(
                deterministic_sample(cleaned, max_samples=max_samples)
            )
            percentiles_approximated = True
    percentile_values_source.sort()
    percentile_sample_count = len(percentile_values_source)
    values_by_percentile = {
        percentile: _percentile_from_sorted(
            percentile_values_source,
            percentile,
            method=method,
        )
        for percentile in requested
    }
    if not cleaned:
        return PercentileSummary(
            sample_count=0,
            minimum=None,
            maximum=None,
            mean=None,
            median=None,
            standard_deviation=None,
            percentile_values=values_by_percentile,
            missing_count=missing_count,
            invalid_count=total_invalid,
            percentile_sample_count=0,
            percentiles_approximated=False,
        )
    return PercentileSummary(
        sample_count=sample_count,
        minimum=min(cleaned),
        maximum=max(cleaned),
        mean=statistics.fmean(cleaned),
        median=statistics.median(cleaned),
        standard_deviation=statistics.pstdev(cleaned),
        percentile_values=values_by_percentile,
        missing_count=missing_count,
        invalid_count=total_invalid,
        percentile_sample_count=percentile_sample_count,
        percentiles_approximated=percentiles_approximated,
    )
