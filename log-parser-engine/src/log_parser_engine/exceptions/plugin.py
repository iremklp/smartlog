from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from log_parser_engine.models import PluginDiscoveryResult


class PluginError(Exception):
    """Base exception for plugin discovery and loading issues."""


class PluginDiscoveryError(PluginError):
    """Raised when a plugin discovery operation cannot complete."""


class PluginLoadError(PluginError):
    """Raised when a plugin cannot be loaded from a supported source."""


class InvalidPluginError(PluginError):
    """Raised when a loaded object does not satisfy the plugin contract."""


class PluginValidationError(InvalidPluginError):
    """Backward-compatible alias for plugin validation failures."""


class PluginFactoryError(PluginError):
    """Raised when a plugin factory cannot produce a parser instance."""


class PluginStartupError(PluginError):
    """Raised when configured startup plugins cannot be initialized safely."""

    def __init__(
        self,
        message: str = "plugin startup failed",
        *,
        result: PluginDiscoveryResult | None = None,
    ) -> None:
        super().__init__(message)
        self.result = result
