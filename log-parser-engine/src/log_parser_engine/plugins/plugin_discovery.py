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

    DEFAULT_MAX_CANDIDATES = 100
    MAX_SOURCE_NAME_LENGTH = 64

    def __init__(
        self,
        *,
        loaders: Iterable[BasePluginLoader] | None = None,
        max_candidates: int = DEFAULT_MAX_CANDIDATES,
    ) -> None:
        if isinstance(max_candidates, bool) or not isinstance(max_candidates, int):
            raise TypeError("max_candidates must be an integer")
        if max_candidates < 1:
            raise ValueError("max_candidates must be at least 1")

        resolved_loaders = tuple(loaders or ())
        for loader in resolved_loaders:
            if not isinstance(loader, BasePluginLoader):
                raise TypeError("loaders must contain only BasePluginLoader instances")

        self._loaders = tuple(sorted(resolved_loaders, key=self._loader_sort_key))
        self._max_candidates = max_candidates

    @property
    def loaders(self) -> tuple[BasePluginLoader, ...]:
        """Return the immutable, deterministic loader snapshot."""

        return self._loaders

    @property
    def max_candidates(self) -> int:
        """Return the maximum candidates accepted from one loader."""

        return self._max_candidates

    def discover_and_register(
        self,
        registry: ParserRegistry | None = None,
        *,
        replace: bool = False,
    ) -> PluginDiscoveryResult:
        results: list[PluginLoadResult] = []
        for loader in self._loaders:
            source_name = self._safe_source_name(loader)
            try:
                candidates = self._discover_candidates(loader)
                if len(candidates) > self._max_candidates:
                    raise PluginDiscoveryError(
                        "plugin candidate limit exceeded"
                    )
            except Exception as exc:  # noqa: BLE001
                results.append(
                    self._failed_result(
                        candidate=self._loader_candidate(source_name),
                        exc=exc,
                        operation="discovery",
                    )
                )
                continue

            valid_candidates: list[PluginCandidate] = []
            for index, candidate in enumerate(candidates):
                if isinstance(candidate, PluginCandidate):
                    valid_candidates.append(candidate)
                    continue
                results.append(
                    self._failed_result(
                        candidate=self._invalid_candidate(source_name, index),
                        exc=PluginDiscoveryError(
                            "loader returned a non-PluginCandidate value"
                        ),
                        operation="discovery",
                    )
                )

            for candidate in sorted(
                valid_candidates,
                key=self._candidate_sort_key,
            ):
                try:
                    loaded_object = self._load_candidate(loader, candidate)
                    parser = resolve_parser_instance(loaded_object)
                    if not isinstance(parser, BaseParser):
                        raise PluginLoadError("resolved object is not a BaseParser")

                    registration = None
                    existed_before_registration = False
                    if registry is not None:
                        existed_before_registration = registry.contains(parser.name)
                        registration = registry.register(
                            parser,
                            origin=f"plugin:{source_name}",
                            replace=replace,
                        )
                    results.append(
                        PluginLoadResult.loaded(
                            candidate=candidate,
                            parser_name=parser.name,
                            parser_version=parser.version,
                            registered=registration is not None,
                            replaced_existing=(
                                replace
                                and existed_before_registration
                                and registration is not None
                            ),
                        )
                    )
                except Exception as exc:  # noqa: BLE001
                    results.append(
                        self._failed_result(
                            candidate=candidate,
                            exc=exc,
                            operation="load",
                        )
                    )

        return PluginDiscoveryResult(
            results=tuple(sorted(results, key=self._result_sort_key))
        )

    def _discover_candidates(
        self,
        loader: BasePluginLoader,
    ) -> tuple[PluginCandidate, ...]:
        candidates = loader.safe_discover()
        if not isinstance(candidates, tuple):
            raise PluginDiscoveryError(
                "plugin loader must return a tuple of candidates"
            )
        return candidates

    def _load_candidate(
        self,
        loader: BasePluginLoader,
        candidate: PluginCandidate,
    ) -> object:
        return loader.safe_load(candidate)

    def _failed_result(
        self,
        *,
        candidate: PluginCandidate,
        exc: Exception,
        operation: str,
    ) -> PluginLoadResult:
        error_type = exc.__class__.__name__
        return PluginLoadResult.failed(
            candidate=candidate,
            error_type=error_type,
            error_message=f"plugin {operation} failed: {error_type}",
        )

    def _loader_candidate(self, source_name: str) -> PluginCandidate:
        return PluginCandidate(
            name=source_name,
            source=source_name,
            module_name=source_name,
            origin=f"plugin:{source_name}",
        )

    def _invalid_candidate(
        self,
        source_name: str,
        index: int,
    ) -> PluginCandidate:
        name = f"{source_name}-candidate-{index}"
        return PluginCandidate(
            name=name,
            source=source_name,
            module_name=name,
            origin=f"plugin:{source_name}",
        )

    def _loader_sort_key(
        self,
        loader: BasePluginLoader,
    ) -> tuple[str, str, str]:
        loader_type = type(loader)
        return (
            self._safe_source_name(loader),
            loader_type.__module__,
            loader_type.__qualname__,
        )

    def _candidate_sort_key(
        self,
        candidate: PluginCandidate,
    ) -> tuple[str, str, str, str, str]:
        return (
            candidate.source.casefold(),
            candidate.module_name.casefold(),
            (candidate.object_name or "").casefold(),
            candidate.name.casefold(),
            candidate.origin.casefold(),
        )

    def _result_sort_key(
        self,
        result: PluginLoadResult,
    ) -> tuple[str, str, str, str, str]:
        return self._candidate_sort_key(result.candidate)

    def _safe_source_name(self, loader: BasePluginLoader) -> str:
        try:
            raw_source_name = loader.source_name
        except Exception:  # noqa: BLE001
            return "unknown"

        cleaned = str(raw_source_name).strip().casefold()
        sanitized = "".join(
            character
            if character.isascii()
            and (character.isalnum() or character in {"-", "_", "."})
            else "_"
            for character in cleaned
        )
        bounded = sanitized[: self.MAX_SOURCE_NAME_LENGTH].strip("._-")
        return bounded or "unknown"
