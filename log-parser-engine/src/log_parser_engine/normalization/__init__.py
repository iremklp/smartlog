from log_parser_engine.models.normalization import NormalizationInput

from .normalizer import (
    Normalizer,
    build_field_mapping,
    normalize_duration,
    normalize_severity,
    normalize_timestamp,
)


class LogNormalizer(Normalizer):
    """Backward-compatible alias for the canonical normalizer."""


__all__ = [
    "LogNormalizer",
    "Normalizer",
    "NormalizationInput",
    "build_field_mapping",
    "normalize_duration",
    "normalize_severity",
    "normalize_timestamp",
]
