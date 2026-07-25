from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class AnalysisOptions(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    max_events: int = 1_000_000
    max_groups: int = 1_000
    default_top_n: int = 10
    max_top_n: int = 100
    max_timeline_buckets: int = 2_000
    default_time_bucket_seconds: int = 300
    max_time_bucket_seconds: int = 31_536_000
    max_percentile_samples: int = 1_000_000
    max_group_fields_per_request: int = 20
    max_percentiles_per_request: int = 20
    max_samples_per_request: int = 100
    max_comparison_metrics_per_request: int = 20
    max_dimension_value_length: int = 256
    percentile_method: Literal["nearest_rank", "linear"] = "nearest_rank"
    duration_field_candidates: tuple[str, ...] = (
        "duration_ms", "latency_ms", "response_time_ms", "elapsed_ms",
        "request_time_ms", "request_time", "duration_us", "latency_us",
    )
    http_status_field_candidates: tuple[str, ...] = (
        "http_status", "status_code", "http.status_code", "status", "sc_status",
    )
    http_method_field_candidates: tuple[str, ...] = (
        "http_method", "method", "http.method", "cs_method",
    )
    http_path_field_candidates: tuple[str, ...] = (
        "http_path", "route_template", "http.route", "path", "url.path",
        "request_path", "uri", "cs_uri_stem",
    )
    max_attribute_depth: int = 10
    strict_numeric_values: bool = True
    ignore_non_finite_values: bool = True
    minimum_comparison_count: int = 10
    significant_change_percent: float = 20.0
    error_rate_warning_threshold: float = 0.05
    error_rate_critical_threshold: float = 0.20
    latency_warning_percentile_ms: float | None = None
    latency_critical_percentile_ms: float | None = None
    strict: bool = True
    allow_percentile_sampling: bool = False
    normalize_endpoint_trailing_slash: bool = True
    minimum_endpoint_requests_for_rate: int = 10
    minimum_endpoint_latency_samples: int = 5
    dominant_group_warning_percentage: float = 50.0
    dominant_group_critical_percentage: float = 80.0

    @field_validator(
        "max_events", "max_groups", "default_top_n", "max_top_n",
        "max_timeline_buckets", "default_time_bucket_seconds",
        "max_time_bucket_seconds",
        "max_percentile_samples", "minimum_comparison_count",
        "minimum_endpoint_requests_for_rate", "minimum_endpoint_latency_samples",
        "max_group_fields_per_request", "max_percentiles_per_request",
        "max_samples_per_request", "max_comparison_metrics_per_request",
        "max_dimension_value_length",
    )
    @classmethod
    def positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("count limits must be positive")
        return value

    @field_validator(
        "duration_field_candidates", "http_status_field_candidates",
        "http_method_field_candidates", "http_path_field_candidates",
    )
    @classmethod
    def candidates(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        result = tuple(dict.fromkeys(item.strip() for item in value if item.strip()))
        if not result:
            raise ValueError("candidate list must not be empty")
        return result

    @field_validator(
        "significant_change_percent",
        "error_rate_warning_threshold",
        "error_rate_critical_threshold",
        "latency_warning_percentile_ms",
        "latency_critical_percentile_ms",
        "dominant_group_warning_percentage",
        "dominant_group_critical_percentage",
    )
    @classmethod
    def finite_threshold(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("analysis thresholds must be finite")
        return value

    @model_validator(mode="after")
    def validate_options(self) -> "AnalysisOptions":
        if self.default_top_n > self.max_top_n:
            raise ValueError("default_top_n cannot exceed max_top_n")
        if self.default_time_bucket_seconds > self.max_time_bucket_seconds:
            raise ValueError(
                "default_time_bucket_seconds cannot exceed "
                "max_time_bucket_seconds"
            )
        if not 1 <= self.max_attribute_depth <= 20:
            raise ValueError("max_attribute_depth must be between 1 and 20")
        if not (
            0
            <= self.error_rate_warning_threshold
            < self.error_rate_critical_threshold
            <= 1
        ):
            raise ValueError("error rate thresholds must be ordered ratios")
        if self.significant_change_percent < 0:
            raise ValueError("significant_change_percent must not be negative")
        warning = self.latency_warning_percentile_ms
        critical = self.latency_critical_percentile_ms
        if warning is not None and warning < 0 or critical is not None and critical < 0:
            raise ValueError("latency thresholds must not be negative")
        if warning is not None and critical is not None and warning > critical:
            raise ValueError("latency warning cannot exceed critical")
        if not (
            0
            <= self.dominant_group_warning_percentage
            < self.dominant_group_critical_percentage
            <= 100
        ):
            raise ValueError(
                "dominant group thresholds must be ordered percentages"
            )
        return self
