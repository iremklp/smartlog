from __future__ import annotations


class PluginError(Exception):
    """Base exception for plugin discovery and loading issues."""


class PluginDiscoveryError(PluginError):
    """Raised when a plugin discovery operation cannot complete."""


class PluginLoadError(PluginError):
    """Raised when a plugin cannot be loaded from a supported source."""


class InvalidPluginError(PluginError):
    """Raised when a loaded object does not satisfy the plugin contract."""


class PluginFactoryError(PluginError):
    """Raised when a plugin factory cannot produce a parser instance."""
