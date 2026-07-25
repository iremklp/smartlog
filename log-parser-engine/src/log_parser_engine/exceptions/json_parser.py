from __future__ import annotations


class JsonParserError(Exception):
    """Base exception for JSON parser failures."""


class JsonParseError(JsonParserError):
    """Backward-compatible alias for parse failures."""


class JsonDecodingError(JsonParserError):
    """Raised when the JSON input cannot be decoded."""


class JsonStructureError(JsonParserError):
    """Raised when the decoded JSON structure is unsupported."""


class JsonFieldPathError(JsonParserError):
    """Raised when field-path resolution fails."""


class JsonProfileError(JsonParserError):
    """Raised when profile detection fails."""


class JsonMappingError(JsonParserError):
    """Raised when mapping to canonical fields fails."""
