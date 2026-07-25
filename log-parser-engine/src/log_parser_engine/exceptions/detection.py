
from __future__ import annotations


class DetectionError(Exception):
    """Base exception for parser detection failures."""


class DetectorInternalError(DetectionError):
    """Raised when the detector itself encounters an unexpected error."""


class NoParserFoundError(DetectionError):
    """Raised when no parser matches a log sample."""


class UnsupportedLogFormatError(DetectionError):
    """Raised when the sample is not supported by any parser."""


class DuplicateParserError(DetectionError):
    """Raised when duplicate parser names are detected."""
