from __future__ import annotations


class ParserRegistryError(Exception):
    """Base exception for parser-registry failures."""


class ParserAlreadyRegisteredError(ParserRegistryError):
    """Raised when attempting to register a parser more than once."""


class ParserNotFoundError(ParserRegistryError):
    """Raised when a requested parser is not registered."""


class ParserRegistrationMismatchError(ParserRegistryError):
    """Raised when registration metadata is inconsistent."""
