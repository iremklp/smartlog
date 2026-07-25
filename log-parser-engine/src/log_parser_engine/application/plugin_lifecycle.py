from __future__ import annotations

import importlib
import threading
from collections.abc import Iterable
from dataclasses import dataclass
from importlib import metadata as importlib_metadata
from time import perf_counter
from typing import Any

from log_parser_engine.core import BaseParser, ParserRegistry
from log_parser_engine.exceptions import (
    ParserAlreadyRegisteredError,
    PluginDiscoveryError,
    PluginStartupError,
    PluginValidationError,
)
from log_parser_engine.models import (
    PluginCandidate,
    PluginDiscoveryResult,
    PluginLoadResult,
)
from log_parser_engine.plugins.base_loader import BasePluginLoader
from log_parser_engine.plugins.entry_point_loader import EntryPointPluginLoader
from log_parser_engine.plugins.options import PluginStartupOptions
from log_parser_engine.plugins.package_loader import PackagePluginLoader
from log_parser_engine.plugins.validation import resolve_parser_instance


@dataclass(frozen=True, slots=True)
class PluginStartupOutcome:
    """Immutable result of one application plugin startup lifecycle."""

    discovery_result: PluginDiscoveryResult
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _LoaderBinding:
    loader: BasePluginLoader
    origin: str
    required: bool
    allowed_entry_point_names: frozenset[str] = frozenset()


@dataclass(slots=True)
class _PendingPlugin:
    candidate: PluginCandidate
    parser: BaseParser
    origin: str
    result_index: int
    replace_existing: bool = False


class PluginStartupLifecycle:
    """Loads trusted startup plugins exactly once before parser services exist."""

    def __init__(
        self,
        options: PluginStartupOptions,
        *,
        injected_loaders: Iterable[BasePluginLoader] | None = None,
    ) -> None:
        if not isinstance(options, PluginStartupOptions):
            raise TypeError("options must be PluginStartupOptions")
        self._options = options
        self._injected_loaders = tuple(injected_loaders or ())
        if self._injected_loaders and not options.allow_injected_loaders:
            raise PluginStartupError(
                "injected plugin loaders require explicit startup opt-in"
            )
        for loader in self._injected_loaders:
            if not isinstance(loader, BasePluginLoader):
                raise PluginStartupError(
                    "injected plugin loaders must implement BasePluginLoader"
                )

        self._lock = threading.RLock()
        self._ran = False
        self._registry: ParserRegistry | None = None
        self._outcome: PluginStartupOutcome | None = None
        self._startup_error: PluginStartupError | None = None

    def run(self, registry: ParserRegistry) -> PluginStartupOutcome:
        """Run once and return the cached immutable outcome on repeated calls."""

        if not isinstance(registry, ParserRegistry):
            raise TypeError("registry must be ParserRegistry")

        with self._lock:
            if self._ran:
                if registry is not self._registry:
                    raise PluginStartupError(
                        "plugin startup lifecycle cannot be reused with another registry"
                    )
                if self._startup_error is not None:
                    raise self._startup_error
                if self._outcome is None:
                    raise PluginStartupError("plugin startup did not produce an outcome")
                return self._outcome

            self._ran = True
            self._registry = registry
            try:
                self._outcome = self._execute(registry)
            except PluginStartupError as exc:
                self._startup_error = exc
                raise
            return self._outcome

    def _execute(self, registry: ParserRegistry) -> PluginStartupOutcome:
        started = perf_counter()
        if not self._options.enabled and not self._injected_loaders:
            return PluginStartupOutcome(
                discovery_result=PluginDiscoveryResult(
                    duration_ms=(perf_counter() - started) * 1000.0
                ),
                warnings=tuple(),
            )

        results: list[PluginLoadResult] = []
        pending: list[_PendingPlugin] = []
        bindings = self._build_loader_bindings(results)
        candidate_count = 0

        for binding in bindings:
            candidates = self._discover_candidates(binding, results)
            if candidates is None:
                continue

            selected = self._filter_entry_point_candidates(
                binding,
                candidates,
                results,
            )
            remaining = self._options.max_candidates - candidate_count
            if len(selected) > remaining:
                selected = selected[: max(0, remaining)]
                results.append(
                    self._failure_result(
                        self._source_candidate(binding),
                        error_type="PluginCandidateLimitError",
                    )
                )
            candidate_count += len(selected)

            if binding.required and not selected:
                if not self._has_failure_for_source(results, binding.loader.source_name):
                    results.append(
                        self._failure_result(
                            self._source_candidate(binding),
                            error_type="PluginDiscoveryError",
                        )
                    )
                continue

            for candidate in selected:
                candidate_started = perf_counter()
                try:
                    loaded = binding.loader.safe_load(candidate)
                    parser = resolve_parser_instance(loaded)
                    self._validate_parser(parser)
                except Exception as exc:  # noqa: BLE001
                    results.append(
                        self._failure_result(
                            candidate,
                            error_type=exc.__class__.__name__,
                            duration_ms=(perf_counter() - candidate_started) * 1000.0,
                        )
                    )
                    continue

                result_index = len(results)
                results.append(
                    PluginLoadResult.loaded(
                        candidate=candidate,
                        parser_name=parser.name,
                        parser_version=parser.version,
                        registered=False,
                        duration_ms=(perf_counter() - candidate_started) * 1000.0,
                    )
                )
                pending.append(
                    _PendingPlugin(
                        candidate=candidate,
                        parser=parser,
                        origin=binding.origin,
                        result_index=result_index,
                    )
                )

        pending = self._apply_duplicate_policy(registry, pending, results)
        pending = self._preflight_registrations(registry, pending, results)

        interim = self._build_result(results, started)
        if interim.has_failures and self._options.failure_policy == "fail":
            raise PluginStartupError(
                f"plugin startup failed with {interim.failed_count} error(s)",
                result=interim,
            )

        self._commit_plugins(registry, pending, results)
        final_result = self._build_result(results, started)
        if final_result.has_failures and self._options.failure_policy == "fail":
            raise PluginStartupError(
                f"plugin startup failed with {final_result.failed_count} error(s)",
                result=final_result,
            )
        return PluginStartupOutcome(
            discovery_result=final_result,
            warnings=self._build_warnings(final_result),
        )

    def _build_loader_bindings(
        self,
        results: list[PluginLoadResult],
    ) -> tuple[_LoaderBinding, ...]:
        bindings: list[_LoaderBinding] = []
        for package_name in self._options.package_names:
            try:
                self._validate_package_manifest(package_name)
                loader = PackagePluginLoader(package_name)
            except Exception as exc:  # noqa: BLE001
                results.append(
                    self._failure_result(
                        self._synthetic_candidate(
                            name=package_name.rsplit(".", 1)[-1],
                            source="package",
                            module_name=package_name,
                        ),
                        error_type=exc.__class__.__name__,
                    )
                )
                continue
            bindings.append(
                _LoaderBinding(
                    loader=loader,
                    origin="plugin:package",
                    required=True,
                )
            )

        if self._options.enable_entry_points:
            # Accessing this function ensures importlib.metadata is loaded in a clean
            # Python process before the backward-compatible loader uses it.
            _ = importlib_metadata.entry_points
            bindings.append(
                _LoaderBinding(
                    loader=EntryPointPluginLoader(
                        group=self._options.entry_point_group
                    ),
                    origin="plugin:entry_point",
                    required=True,
                    allowed_entry_point_names=frozenset(
                        self._options.entry_point_names
                    ),
                )
            )

        bindings.extend(
            _LoaderBinding(
                loader=loader,
                origin="plugin:injected",
                required=False,
            )
            for loader in self._injected_loaders
        )
        return tuple(bindings)

    def _validate_package_manifest(self, package_name: str) -> None:
        package = importlib.import_module(package_name)
        if not self._options.require_package_manifest:
            return
        manifest = getattr(package, "__plugin_modules__", None)
        if (
            manifest is None
            or isinstance(manifest, (str, bytes))
            or not isinstance(manifest, Iterable)
        ):
            raise PluginDiscoveryError("configured package has no plugin manifest")
        normalized = tuple(str(item).strip() for item in manifest if str(item).strip())
        if not normalized:
            raise PluginDiscoveryError("configured package has an empty plugin manifest")
        for module_name in normalized:
            parts = module_name.split(".")
            if any(not part.isidentifier() or part.startswith("_") for part in parts):
                raise PluginDiscoveryError("plugin manifest contains an invalid module")

    def _discover_candidates(
        self,
        binding: _LoaderBinding,
        results: list[PluginLoadResult],
    ) -> tuple[PluginCandidate, ...] | None:
        try:
            discovered = binding.loader.safe_discover()
        except Exception as exc:  # noqa: BLE001
            results.append(
                self._failure_result(
                    self._source_candidate(binding),
                    error_type=exc.__class__.__name__,
                )
            )
            return None
        return tuple(
            sorted(
                discovered,
                key=lambda candidate: (
                    candidate.source,
                    candidate.origin,
                    candidate.module_name,
                    candidate.object_name or "",
                ),
            )
        )

    def _filter_entry_point_candidates(
        self,
        binding: _LoaderBinding,
        candidates: tuple[PluginCandidate, ...],
        results: list[PluginLoadResult],
    ) -> tuple[PluginCandidate, ...]:
        allowed = binding.allowed_entry_point_names
        if not allowed:
            return candidates

        selected = tuple(
            candidate
            for candidate in candidates
            if candidate.entry_point_name in allowed
        )
        found = {
            candidate.entry_point_name
            for candidate in selected
            if candidate.entry_point_name is not None
        }
        for missing_name in sorted(allowed - found):
            results.append(
                self._failure_result(
                    self._synthetic_candidate(
                        name=missing_name,
                        source="entry_point",
                        module_name=self._options.entry_point_group,
                    ),
                    error_type="PluginEntryPointNotFoundError",
                )
            )
        return selected

    def _validate_parser(self, parser: BaseParser) -> None:
        metadata = parser.metadata
        if metadata.experimental and not self._options.allow_experimental_plugins:
            raise PluginValidationError("experimental plugins are not enabled")
        if self._options.require_thread_safe_plugins and not metadata.thread_safe:
            raise PluginValidationError("plugin parser must be thread safe")

    def _apply_duplicate_policy(
        self,
        registry: ParserRegistry,
        pending: list[_PendingPlugin],
        results: list[PluginLoadResult],
    ) -> list[_PendingPlugin]:
        planned_origins = {
            registration.parser_name.strip().casefold(): registration.origin
            for registration in registry.list_registrations()
        }
        accepted: list[_PendingPlugin] = []
        for item in pending:
            normalized_name = item.parser.name.strip().casefold()
            existing_origin = planned_origins.get(normalized_name)
            if existing_origin is not None or registry.contains(item.parser.name):
                if self._options.duplicate_policy == "reject":
                    results[item.result_index] = self._failure_result(
                        item.candidate,
                        error_type=ParserAlreadyRegisteredError.__name__,
                        duration_ms=results[item.result_index].duration_ms,
                    )
                    continue
                if (
                    existing_origin == "builtin"
                    and not self._options.allow_builtin_replacement
                ):
                    results[item.result_index] = self._failure_result(
                        item.candidate,
                        error_type="BuiltinParserReplacementDisabledError",
                        duration_ms=results[item.result_index].duration_ms,
                    )
                    continue
                item.replace_existing = True

            planned_origins[normalized_name] = item.origin
            accepted.append(item)
        return accepted

    def _preflight_registrations(
        self,
        registry: ParserRegistry,
        pending: list[_PendingPlugin],
        results: list[PluginLoadResult],
    ) -> list[_PendingPlugin]:
        try:
            staged_registry = self._copy_registry(registry)
        except Exception as exc:  # noqa: BLE001
            raise PluginStartupError(
                "plugin startup could not stage the parser registry"
            ) from exc

        accepted: list[_PendingPlugin] = []
        for item in pending:
            try:
                staged_registry.register(
                    item.parser,
                    origin=item.origin,
                    replace=item.replace_existing,
                )
            except Exception as exc:  # noqa: BLE001
                results[item.result_index] = self._failure_result(
                    item.candidate,
                    error_type=exc.__class__.__name__,
                    duration_ms=results[item.result_index].duration_ms,
                )
                continue
            accepted.append(item)
        return accepted

    def _copy_registry(self, registry: ParserRegistry) -> ParserRegistry:
        staged = ParserRegistry()
        for registration in registry.list_registrations():
            staged.register(
                registry.get(registration.parser_name),
                enabled=registration.enabled,
                origin=registration.origin,
                notes=registration.notes,
            )
        return staged

    def _commit_plugins(
        self,
        registry: ParserRegistry,
        pending: list[_PendingPlugin],
        results: list[PluginLoadResult],
    ) -> None:
        for item in pending:
            try:
                registry.register(
                    item.parser,
                    origin=item.origin,
                    replace=item.replace_existing,
                )
            except Exception as exc:  # noqa: BLE001
                results[item.result_index] = self._failure_result(
                    item.candidate,
                    error_type=exc.__class__.__name__,
                    duration_ms=results[item.result_index].duration_ms,
                )
                continue
            previous = results[item.result_index]
            results[item.result_index] = PluginLoadResult.loaded(
                candidate=item.candidate,
                parser_name=item.parser.name,
                parser_version=item.parser.version,
                registered=True,
                replaced_existing=item.replace_existing,
                duration_ms=previous.duration_ms,
            )

    def _build_result(
        self,
        results: list[PluginLoadResult],
        started: float,
    ) -> PluginDiscoveryResult:
        return PluginDiscoveryResult(
            results=tuple(results),
            duration_ms=(perf_counter() - started) * 1000.0,
        )

    def _build_warnings(
        self,
        result: PluginDiscoveryResult,
    ) -> tuple[str, ...]:
        warnings = [
            self._sanitize_warning(
                f"{load_result.candidate.source} plugin "
                f"'{self._safe_token(load_result.candidate.name)}' failed "
                f"({self._safe_token(load_result.error_type or 'PluginError')})"
            )
            for load_result in result.results
            if not load_result.success
        ]
        maximum = self._options.max_startup_warnings
        if len(warnings) <= maximum:
            return tuple(warnings)
        omitted = len(warnings) - maximum + 1
        summary = self._sanitize_warning(
            f"{omitted} additional plugin startup warning(s) omitted"
        )
        return tuple([*warnings[: maximum - 1], summary])

    def _sanitize_warning(self, value: str) -> str:
        cleaned = "".join(
            character if ord(character) >= 32 else " " for character in value
        ).strip()
        maximum = self._options.max_warning_length
        if len(cleaned) <= maximum:
            return cleaned
        return f"{cleaned[: maximum - 3]}..."

    def _safe_token(self, value: str) -> str:
        cleaned = "".join(
            character
            for character in value
            if character.isalnum() or character in {"_", "-", "."}
        )
        return cleaned[:64] or "unknown"

    def _failure_result(
        self,
        candidate: PluginCandidate,
        *,
        error_type: str,
        duration_ms: float = 0.0,
    ) -> PluginLoadResult:
        return PluginLoadResult.failed(
            candidate=candidate,
            error_type=self._safe_token(error_type),
            error_message="plugin startup operation failed",
            duration_ms=max(0.0, duration_ms),
        )

    def _source_candidate(self, binding: _LoaderBinding) -> PluginCandidate:
        source = self._safe_token(binding.loader.source_name)
        return self._synthetic_candidate(
            name=source,
            source=source,
            module_name=source,
        )

    def _synthetic_candidate(
        self,
        *,
        name: str,
        source: str,
        module_name: str,
    ) -> PluginCandidate:
        safe_name = self._safe_token(name)
        safe_source = self._safe_token(source)
        safe_module = self._safe_token(module_name)
        return PluginCandidate(
            name=safe_name,
            source=safe_source,
            module_name=safe_module,
            origin=f"{safe_source}:{safe_name}",
            entry_point_group=(
                self._options.entry_point_group
                if safe_source == "entry_point"
                else None
            ),
            entry_point_name=safe_name if safe_source == "entry_point" else None,
        )

    def _has_failure_for_source(
        self,
        results: list[PluginLoadResult],
        source_name: str,
    ) -> bool:
        normalized_source = self._safe_token(source_name)
        return any(
            not result.success
            and self._safe_token(result.candidate.source) == normalized_source
            for result in results
        )

