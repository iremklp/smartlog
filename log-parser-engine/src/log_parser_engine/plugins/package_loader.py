from __future__ import annotations

import importlib
import pkgutil
from typing import Any

from log_parser_engine.exceptions import (
    InvalidPluginError,
    PluginDiscoveryError,
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

        module_names = self._discover_module_names(package)
        candidates: list[PluginCandidate] = []
        for module_name in module_names:
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
        if candidate.source != "package":
            raise PluginLoadError("candidate source is not package")

        module = importlib.import_module(candidate.module_name)
        loaded_object = self._resolve_module_object(module)
        return resolve_parser_instance(loaded_object)

    def _discover_module_names(self, package: Any) -> list[str]:
        module_names = []
        for module_info in pkgutil.walk_packages(
            package.__path__,
            prefix=f"{self._package_name}.",
            onerror=lambda _exc: None,
        ):
            module_names.append(module_info.name)

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
            and issubclass(value, object)
            and value.__module__ == module.__name__
            and value.__name__ != "BaseParser"
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

    def _is_private_module(self, module_name: str) -> bool:
        parts = module_name.split(".")
        return any(part.startswith("_") for part in parts)
