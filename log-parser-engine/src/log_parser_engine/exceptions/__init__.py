"""Exceptions for detection, parser selection, and plugin loading."""

from .detection import DetectionError, DuplicateParserError
from .parser_registry import (
    ParserAlreadyRegisteredError,
    ParserNotFoundError,
    ParserRegistrationMismatchError,
    ParserRegistryError,
)
from .plugin import (
    InvalidPluginError,
    PluginDiscoveryError,
    PluginError,
    PluginFactoryError,
    PluginLoadError,
)

__all__ = [
    "DetectionError",
    "DuplicateParserError",
    "InvalidPluginError",
    "ParserAlreadyRegisteredError",
    "ParserNotFoundError",
    "ParserRegistrationMismatchError",
    "ParserRegistryError",
    "PluginDiscoveryError",
    "PluginError",
    "PluginFactoryError",
    "PluginLoadError",
]
