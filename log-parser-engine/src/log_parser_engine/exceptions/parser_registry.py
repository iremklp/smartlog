from __future__ import annotations


class ParserRegistryError(Exception):
    """Base exception for parser-registry failures."""


class ParserConfigurationError(ParserRegistryError):
    """Raised when parser registry configuration is invalid."""


class ParserDiscoveryError(ParserRegistryError):
    """Raised when parser discovery fails."""


class ParserRegistrationError(ParserRegistryError):
    """Raised when a parser cannot be registered."""


class ParserAlreadyRegisteredError(ParserRegistryError):
    """Raised when attempting to register a parser more than once."""


class ParserNotFoundError(ParserRegistryError):
    """Raised when a requested parser is not registered."""


class ParserRegistrationMismatchError(ParserRegistryError):
    """Raised when registration metadata is inconsistent."""
