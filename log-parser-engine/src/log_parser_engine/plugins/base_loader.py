from __future__ import annotations

from abc import ABC, abstractmethod

from log_parser_engine.exceptions import PluginDiscoveryError, PluginLoadError
from log_parser_engine.models import PluginCandidate


class BasePluginLoader(ABC):
    """Abstract contract for plugin discovery sources."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return a stable human-readable source name."""

    @abstractmethod
    def discover(self) -> tuple[PluginCandidate, ...]:
        """Discover plugin candidates from the loader source."""

    @abstractmethod
    def load(self, candidate: PluginCandidate) -> object:
        """Load a Python object from a plugin candidate."""

    def safe_discover(self) -> tuple[PluginCandidate, ...]:
        try:
            return self.discover()
        except Exception as exc:  # noqa: BLE001
            raise PluginDiscoveryError(
                f"{self.source_name} discovery failed: {exc.__class__.__name__}"
            ) from exc

    def safe_load(self, candidate: PluginCandidate) -> object:
        try:
            return self.load(candidate)
        except Exception as exc:  # noqa: BLE001
            raise PluginLoadError(
                f"{self.source_name} load failed for {candidate.qualified_name}: "
                f"{exc.__class__.__name__}"
            ) from exc
