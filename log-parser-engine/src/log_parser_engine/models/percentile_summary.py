"""Percentile and descriptive statistics model."""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .immutable import FrozenDict


class PercentileSummary(BaseModel):
    """Exact or explicitly sampled descriptive statistics for numeric values.

    ``standard_deviation`` represents population standard deviation. Count,
    extrema, mean, and standard deviation can be computed over every valid
    value with constant memory. When bounded sampling is used, median and the
    requested percentile values are order-statistic estimates over the smaller
    deterministic sample recorded by ``percentile_sample_count``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    sample_count: int = Field(ge=0)
    minimum: float | None = None
    maximum: float | None = None
    mean: float | None = None
    median: float | None = None
    standard_deviation: float | None = Field(default=None, ge=0)
    percentile_values: dict[float, float | None] = Field(default_factory=FrozenDict)
    missing_count: int = Field(default=0, ge=0)
    invalid_count: int = Field(default=0, ge=0)
    percentile_sample_count: int | None = Field(default=None, ge=0)
    percentiles_approximated: bool = False

    @field_validator(
        "minimum",
        "maximum",
        "mean",
        "median",
        "standard_deviation",
    )
    @classmethod
    def _finite_statistics(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("percentile statistics must be finite")
        return value

    @field_validator("percentile_values")
    @classmethod
    def _percentiles(
        cls,
        value: dict[float, float | None],
    ) -> dict[float, float | None]:
        normalized: dict[float, float | None] = {}
        for raw_percentile, raw_value in value.items():
            percentile = float(raw_percentile)
            if (
                not math.isfinite(percentile)
                or percentile < 0
                or percentile > 100
            ):
                raise ValueError("percentile keys must be between 0 and 100")
            if raw_value is not None and not math.isfinite(raw_value):
                raise ValueError("percentile values must be finite")
            normalized[percentile] = raw_value
        return FrozenDict(normalized)

    @model_validator(mode="after")
    def _sample_consistency(self) -> "PercentileSummary":
        statistics = (
            self.minimum,
            self.maximum,
            self.mean,
            self.median,
            self.standard_deviation,
        )
        if self.sample_count == 0:
            if any(item is not None for item in statistics):
                raise ValueError("empty samples cannot have descriptive statistics")
            if any(item is not None for item in self.percentile_values.values()):
                raise ValueError("empty samples cannot have percentile values")
        elif any(item is None for item in statistics):
            raise ValueError("non-empty samples require all descriptive statistics")
        if (
            self.minimum is not None
            and self.maximum is not None
            and self.minimum > self.maximum
        ):
            raise ValueError("minimum cannot exceed maximum")
        if (
            self.percentile_sample_count is not None
            and self.percentile_sample_count > self.sample_count
        ):
            raise ValueError(
                "percentile_sample_count cannot exceed sample_count"
            )
        if self.percentiles_approximated:
            if (
                self.sample_count == 0
                or self.percentile_sample_count is None
                or self.percentile_sample_count >= self.sample_count
            ):
                raise ValueError(
                    "approximated percentiles require a smaller non-empty sample"
                )
        elif (
            self.percentile_sample_count is not None
            and self.percentile_sample_count != self.sample_count
        ):
            raise ValueError(
                "exact percentiles must use the complete valid sample"
            )
        return self
