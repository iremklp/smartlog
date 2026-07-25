"""Typed failures raised by the statistical analysis subsystem."""

from __future__ import annotations


class AnalysisError(Exception):
    """Base class for safe, user-facing analysis failures."""


class AnalysisConfigurationError(AnalysisError):
    """Raised when analysis engine configuration is invalid."""


class AnalysisRequestError(AnalysisError):
    """Raised when a structurally valid request cannot be executed."""


class AnalysisEventLimitError(AnalysisRequestError):
    """Raised when an analysis snapshot exceeds the configured event limit."""

    def __init__(self, count: int, limit: int) -> None:
        self.count = count
        self.limit = limit
        super().__init__(f"analysis event count {count} exceeds limit {limit}")


class AnalysisConcurrencyLimitError(AnalysisRequestError):
    """Raised when all bounded analysis execution slots are occupied."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        super().__init__(f"concurrent analysis operation limit {limit} reached")


class AnalysisGroupLimitError(AnalysisRequestError):
    """Raised when exact grouping would exceed the configured group limit."""

    def __init__(self, field: str, count: int, limit: int) -> None:
        self.field = field
        self.count = count
        self.limit = limit
        super().__init__(f"group count for {field!r} exceeds limit {limit}")


class AnalysisTimelineLimitError(AnalysisRequestError):
    """Raised when a requested timeline cannot fit the configured bucket limit."""


class AnalysisSampleLimitError(AnalysisRequestError):
    """Raised when an exact numeric sample exceeds the configured sample limit."""


class AnalysisNumericValueError(AnalysisRequestError):
    """Raised when a configured numeric field contains an invalid value."""


class AnalysisFieldResolutionError(AnalysisRequestError):
    """Raised when a configured field cannot be resolved safely."""


class AnalysisComparisonError(AnalysisRequestError):
    """Raised when a comparison cannot be evaluated safely."""


class AnalysisInsufficientDataError(AnalysisRequestError):
    """Raised when an operation explicitly requires more observations."""
