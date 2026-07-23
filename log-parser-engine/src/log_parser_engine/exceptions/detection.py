class DetectionError(Exception):
    """Raised for invalid detection configuration or runtime misuse."""


class DuplicateParserError(DetectionError):
    """Raised when a detector receives multiple parsers with the same name."""
