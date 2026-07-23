from __future__ import annotations

from typing import Iterable

from log_parser_engine.core import ParserRegistry
from log_parser_engine.core.base_parser import BaseParser
from log_parser_engine.exceptions import PluginDiscoveryError, PluginLoadError
from log_parser_engine.models import (
    PluginCandidate,
    PluginDiscoveryResult,
    PluginLoadResult,
)

from .base_loader import BasePluginLoader
from .validation import resolve_parser_instance


class PluginDiscovery:
    """Orchestrates plugin discovery, validation, and safe registration."""

    def __init__(self, *, loaders: Iterable[BasePluginLoader] | None = None) -> None:
        self._loaders = tuple(loaders or ())

    def discover_and_register(
        self,
        registry: ParserRegistry | None = None,
        *,
        replace: bool = False,
    ) -> PluginDiscoveryResult:
        results: list[PluginLoadResult] = []
        for loader in self._loaders:
            try:
                candidates = self._discover_candidates(loader)
            except PluginDiscoveryError as exc:
                results.append(
                    PluginLoadResult.failed(
                        candidate=PluginCandidate(
                            name=loader.source_name,
                            source=loader.source_name,
                            module_name=loader.source_name,
                            origin=loader.source_name,
                        ),
                        error_type=PluginDiscoveryError.__name__,
                        error_message=str(exc),
                    )
                )
                continue

            for candidate in candidates:
                try:
                    loaded_object = self._load_candidate(loader, candidate)
                    parser = resolve_parser_instance(loaded_object)
                    if not isinstance(parser, BaseParser):
                        raise PluginLoadError("resolved object is not a BaseParser")

                    registration = None
                    if registry is not None:
                        registration = registry.register(parser, replace=replace)
                    results.append(
                        PluginLoadResult.loaded(
                            candidate=candidate,
                            parser_name=parser.name,
                            parser_version=parser.version,
                            registered=registration is not None,
                            replaced_existing=replace and registration is not None,
                        )
                    )
                except Exception as exc:  # noqa: BLE001
                    results.append(
                        PluginLoadResult.failed(
                            candidate=candidate,
                            error_type=exc.__class__.__name__,
                            error_message=str(exc),
                        )
                    )

        return PluginDiscoveryResult(results=tuple(results))

    def _discover_candidates(
        self,
        loader: BasePluginLoader,
    ) -> tuple[PluginCandidate, ...]:
        if hasattr(loader, "safe_discover"):
            return loader.safe_discover()  # type: ignore[no-any-return]
        if hasattr(loader, "discover"):
            return loader.discover()  # type: ignore[no-any-return]
        raise PluginDiscoveryError("loader does not support discovery")

    def _load_candidate(
        self,
        loader: BasePluginLoader,
        candidate: PluginCandidate,
    ) -> object:
        if hasattr(loader, "safe_load"):
            return loader.safe_load(candidate)  # type: ignore[no-any-return]
        if hasattr(loader, "load"):
            return loader.load(candidate)  # type: ignore[no-any-return]
        raise PluginLoadError("loader does not support loading")
