from __future__ import annotations


class AnalysisError(Exception):
    """Base class for safe, user-facing analysis failures."""


class AnalysisConfigurationError(AnalysisError):
    pass


class AnalysisRequestError(AnalysisError):
    pass


class AnalysisEventLimitError(AnalysisError):
    def __init__(self, count: int, limit: int) -> None:
        self.count = count
        self.limit = limit
        super().__init__(f"analysis event count {count} exceeds limit {limit}")


class AnalysisGroupLimitError(AnalysisError):
    def __init__(self, field: str, count: int, limit: int) -> None:
        self.field = field
        self.count = count
        self.limit = limit
        super().__init__(f"group count for {field!r} exceeds limit {limit}")


class AnalysisTimelineLimitError(AnalysisError):
    pass


class AnalysisSampleLimitError(AnalysisError):
    pass


class AnalysisNumericValueError(AnalysisError):
    pass


class AnalysisFieldResolutionError(AnalysisError):
    pass


class AnalysisComparisonError(AnalysisError):
    pass


class AnalysisInsufficientDataError(AnalysisError):
    pass
