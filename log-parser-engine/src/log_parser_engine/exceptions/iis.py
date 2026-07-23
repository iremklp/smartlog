from __future__ import annotations


class IisParserError(Exception):
    """Base error for IIS parser failures."""


class IisHeaderError(IisParserError):
    """Raised when IIS header directives are malformed."""


class IisTokenizationError(IisParserError):
    """Raised when an IIS data line cannot be tokenized safely."""


class IisFieldMappingError(IisParserError):
    """Raised when IIS values cannot be mapped cleanly."""
