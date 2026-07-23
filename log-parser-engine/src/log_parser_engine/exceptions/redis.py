from __future__ import annotations


class RedisParserError(Exception):
    """Base class for Redis parser errors."""


class RedisTokenizationError(RedisParserError):
    """Raised when a Redis log line cannot be tokenized."""


class RedisTimestampError(RedisParserError):
    """Raised when a Redis timestamp cannot be parsed."""


class RedisClassificationError(RedisParserError):
    """Raised when Redis event classification fails."""


class RedisMappingError(RedisParserError):
    """Raised when Redis event mapping fails."""
