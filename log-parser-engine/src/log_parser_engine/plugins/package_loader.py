from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Iterable
from typing import Any

from log_parser_engine.core.base_parser import BaseParser
from log_parser_engine.exceptions import (
    InvalidPluginError,
    PluginDiscoveryError,
    PluginError,
    PluginLoadError,
)
from log_parser_engine.models import PluginCandidate

from .base_loader import BasePluginLoader
from .validation import resolve_parser_instance


class PackagePluginLoader(BasePluginLoader):
    """Discover plugins from a Python package module tree."""

    def __init__(
        self,
        package_name: str,
        *,
        recursive: bool = True,
        include_package_module: bool = False,
        require_manifest: bool = False,
        object_names: tuple[str, ...] = (
            "parser",
            "PARSER",
            "Parser",
            "create_parser",
        ),
    ) -> None:
        cleaned_package_name = package_name.strip()
        if not cleaned_package_name:
            raise ValueError("package_name must not be empty")
        self._package_name = cleaned_package_name
        self._recursive = recursive
        self._include_package_module = include_package_module
        self._require_manifest = require_manifest
        self._object_names = self._normalize_object_names(object_names)

    @property
    def source_name(self) -> str:
        return "package"

    def discover(self) -> tuple[PluginCandidate, ...]:
        try:
            package = importlib.import_module(self._package_name)
        except Exception as exc:  # noqa: BLE001
            raise PluginDiscoveryError(
                f"unable to import package {self._package_name}"
            ) from exc

        allowed_module_names = self._allowed_module_names(package)
        if self._require_manifest and allowed_module_names is None:
            raise PluginDiscoveryError("plugin package manifest is required")

        package_path = getattr(package, "__path__", None)
        if package_path is None:
            if self._include_package_module:
                return (
                    PluginCandidate(
                        name=self._package_name,
                        source="package",
                        module_name=self._package_name,
                        origin=f"package:{self._package_name}",
                    ),
                )
            raise PluginDiscoveryError(f"{self._package_name} is not a package")

        module_names = (
            self._discover_module_names(package)
            if allowed_module_names is None
            else sorted(allowed_module_names)
        )
        candidates: list[PluginCandidate] = []
        for module_name in module_names:
            if not self._is_package_module(module_name):
                continue
            if not self._recursive and not self._is_direct_child(module_name):
                continue
            if self._is_private_module(module_name):
                continue
            if module_name == f"{self._package_name}.__init__":
                continue
            if module_name == self._package_name:
                if not self._include_package_module:
                    continue
            candidates.append(
                PluginCandidate(
                    name=module_name.rsplit(".", 1)[-1],
                    source="package",
                    module_name=module_name,
                    origin=f"package:{module_name}",
                )
            )

        return tuple(sorted(candidates, key=lambda candidate: candidate.module_name))

    def load(self, candidate: PluginCandidate) -> object:
        self._validate_candidate(candidate)
        try:
            module = importlib.import_module(candidate.module_name)
        except Exception as exc:  # noqa: BLE001
            raise PluginLoadError("unable to import plugin module") from exc

        try:
            loaded_object = self._resolve_module_object(module)
            return resolve_parser_instance(loaded_object)
        except PluginError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise PluginLoadError("plugin module could not be loaded") from exc

    def _discover_module_names(self, package: Any) -> list[str]:
        module_names: list[str] = []
        discovery_failed = False

        def mark_discovery_failure(_module_name: str) -> None:
            nonlocal discovery_failed
            discovery_failed = True

        try:
            if self._recursive:
                modules: Iterable[pkgutil.ModuleInfo] = pkgutil.walk_packages(
                    package.__path__,
                    prefix=f"{self._package_name}.",
                    onerror=mark_discovery_failure,
                )
            else:
                modules = pkgutil.iter_modules(
                    package.__path__,
                    prefix=f"{self._package_name}.",
                )
            module_names.extend(module_info.name for module_info in modules)
        except Exception as exc:  # noqa: BLE001
            raise PluginDiscoveryError("package module discovery failed") from exc

        if discovery_failed:
            raise PluginDiscoveryError("package module discovery failed")

        if self._include_package_module and self._package_name not in module_names:
            module_names.append(self._package_name)
        return sorted(module_names)

    def _resolve_module_object(self, module: Any) -> object:
        if not hasattr(module, "__dict__"):
            raise InvalidPluginError("module has no __dict__")

        for object_name in self._object_names:
            if hasattr(module, object_name):
                return getattr(module, object_name)

        public_subclasses = [
            value
            for value in module.__dict__.values()
            if isinstance(value, type)
            and issubclass(value, BaseParser)
            and value is not BaseParser
            and value.__module__ == module.__name__
            and not value.__name__.startswith("_")
        ]
        if len(public_subclasses) == 1:
            return public_subclasses[0]
        if len(public_subclasses) > 1:
            raise InvalidPluginError("multiple parser subclasses found")
        raise InvalidPluginError("no plugin object found")

    def _normalize_object_names(self, object_names: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        normalized: list[str] = []
        for raw_name in object_names:
            cleaned = str(raw_name).strip()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            normalized.append(cleaned)
        if not normalized:
            raise ValueError("object_names must contain at least one entry")
        return tuple(normalized)

    def _allowed_module_names(self, package: Any) -> set[str] | None:
        raw_allowed = getattr(package, "__plugin_modules__", None)
        if raw_allowed is None:
            return None
        if isinstance(raw_allowed, (str, bytes)) or not isinstance(
            raw_allowed, Iterable
        ):
            raise PluginDiscoveryError("plugin package manifest is invalid")

        allowed: set[str] = set()
        for module_name in raw_allowed:
            cleaned = str(module_name).strip()
            if not cleaned:
                continue
            qualified = (
                cleaned
                if cleaned == self._package_name
                or cleaned.startswith(f"{self._package_name}.")
                else f"{self._package_name}.{cleaned}"
            )
            if not self._is_valid_module_name(qualified):
                raise PluginDiscoveryError("plugin package manifest is invalid")
            if not self._is_package_module(qualified):
                raise PluginDiscoveryError("plugin package manifest is invalid")
            allowed.add(qualified)
        return allowed

    def _is_private_module(self, module_name: str) -> bool:
        relative_name = module_name.removeprefix(self._package_name).lstrip(".")
        parts = relative_name.split(".")
        return any(part.startswith("_") for part in parts)

    def _validate_candidate(self, candidate: PluginCandidate) -> None:
        if candidate.source != "package":
            raise PluginLoadError("candidate source is not package")
        if not self._is_valid_module_name(candidate.module_name):
            raise PluginLoadError("candidate module name is invalid")
        if not self._is_package_module(candidate.module_name):
            raise PluginLoadError("candidate module is outside the configured package")
        if (
            candidate.module_name == self._package_name
            and not self._include_package_module
        ):
            raise PluginLoadError("package module candidates are disabled")

        try:
            package = importlib.import_module(self._package_name)
            allowed_module_names = self._allowed_module_names(package)
        except PluginDiscoveryError as exc:
            raise PluginLoadError("plugin package manifest is invalid") from exc
        except Exception as exc:  # noqa: BLE001
            raise PluginLoadError("unable to import plugin package") from exc

        if self._require_manifest and allowed_module_names is None:
            raise PluginLoadError("plugin package manifest is required")
        if (
            allowed_module_names is not None
            and candidate.module_name not in allowed_module_names
        ):
            raise PluginLoadError("candidate module is not allowed by the manifest")

    def _is_package_module(self, module_name: str) -> bool:
        return module_name == self._package_name or module_name.startswith(
            f"{self._package_name}."
        )

    def _is_direct_child(self, module_name: str) -> bool:
        if module_name == self._package_name:
            return True
        relative_name = module_name.removeprefix(f"{self._package_name}.")
        return "." not in relative_name

    def _is_valid_module_name(self, module_name: str) -> bool:
        return bool(module_name) and all(
            segment.isidentifier() for segment in module_name.split(".")
        )
