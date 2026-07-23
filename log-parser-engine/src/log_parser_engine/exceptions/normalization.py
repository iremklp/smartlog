from __future__ import annotations


class NormalizationError(Exception):
    """Raised when a payload cannot be normalized into a LogEvent."""
