from __future__ import annotations

from collections.abc import Iterable
from importlib import metadata as importlib_metadata
from typing import Any

from log_parser_engine.exceptions import (
    PluginDiscoveryError,
    PluginError,
    PluginLoadError,
)
from log_parser_engine.models import PluginCandidate

from .base_loader import BasePluginLoader
from .validation import resolve_parser_instance


def _entry_point_matches(entry_points: Any, group: str) -> Iterable[object]:
    if hasattr(entry_points, "select"):
        return list(entry_points.select(group=group))
    if isinstance(entry_points, dict):
        return list(entry_points.get(group, []))
    return []


class EntryPointPluginLoader(BasePluginLoader):
    """Discover plugins from Python entry points."""

    def __init__(
        self,
        *,
        group: str = "log_parser_engine.parsers",
        name_allowlist: tuple[str, ...] | None = None,
    ) -> None:
        self._group = self._validate_group(group)
        self._name_allowlist = self._normalize_name_allowlist(name_allowlist)

    @property
    def source_name(self) -> str:
        return "entry_point"

    def discover(self) -> tuple[PluginCandidate, ...]:
        try:
            entry_points = importlib_metadata.entry_points()
            matches = _entry_point_matches(entry_points, self._group)
        except Exception as exc:  # noqa: BLE001
            raise PluginDiscoveryError("entry point discovery failed") from exc

        candidates: list[PluginCandidate] = []
        for entry_point in matches:
            try:
                name, module_name, object_name = self._entry_point_identity(
                    entry_point
                )
            except (TypeError, ValueError) as exc:
                raise PluginDiscoveryError(
                    "entry point metadata is invalid"
                ) from exc
            if (
                self._name_allowlist is not None
                and name not in self._name_allowlist
            ):
                continue
            candidates.append(
                PluginCandidate(
                    name=name,
                    source="entry_point",
                    module_name=module_name,
                    object_name=object_name,
                    entry_point_group=self._group,
                    entry_point_name=name,
                    origin=f"entry_point:{self._group}:{name}",
                )
            )
        return tuple(sorted(candidates, key=self._candidate_sort_key))

    def load(self, candidate: PluginCandidate) -> object:
        self._validate_candidate(candidate)

        try:
            entry_points = importlib_metadata.entry_points()
            matches = _entry_point_matches(entry_points, self._group)
        except Exception as exc:  # noqa: BLE001
            raise PluginLoadError("entry point metadata could not be read") from exc

        for entry_point in matches:
            try:
                name, module_name, object_name = self._entry_point_identity(
                    entry_point
                )
            except (TypeError, ValueError):
                continue
            if (
                name == candidate.entry_point_name
                and module_name == candidate.module_name
                and object_name == candidate.object_name
            ):
                try:
                    load_method = getattr(entry_point, "load", None)
                    if not callable(load_method):
                        raise PluginLoadError("entry point is not callable")
                    loaded = load_method()
                    return resolve_parser_instance(loaded)
                except PluginError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    raise PluginLoadError("entry point load failed") from exc

        raise PluginLoadError("entry point was not found")

    def _validate_candidate(self, candidate: PluginCandidate) -> None:
        if candidate.source != "entry_point":
            raise PluginLoadError("candidate source is not entry_point")
        if candidate.entry_point_group != self._group:
            raise PluginLoadError("candidate entry point group is invalid")
        if candidate.entry_point_name is None:
            raise PluginLoadError("candidate entry point name is missing")
        try:
            validated_name = self._validate_name(candidate.entry_point_name)
            self._validate_module_name(candidate.module_name)
            self._validate_object_name(candidate.object_name)
        except ValueError as exc:
            raise PluginLoadError("candidate entry point metadata is invalid") from exc
        if candidate.name != validated_name:
            raise PluginLoadError("candidate entry point name is inconsistent")
        if (
            self._name_allowlist is not None
            and validated_name not in self._name_allowlist
        ):
            raise PluginLoadError("candidate entry point is not allowed")

    def _entry_point_identity(
        self,
        entry_point: object,
    ) -> tuple[str, str, str | None]:
        name = self._validate_name(str(getattr(entry_point, "name", "")))
        module_name = str(getattr(entry_point, "module", ""))
        self._validate_module_name(module_name)
        raw_object_name = getattr(entry_point, "attr", None)
        object_name = None if raw_object_name is None else str(raw_object_name)
        self._validate_object_name(object_name)
        return name, module_name, object_name

    def _candidate_sort_key(
        self,
        candidate: PluginCandidate,
    ) -> tuple[str, str, str, str, str]:
        name = candidate.entry_point_name or candidate.name
        object_name = candidate.object_name or ""
        return (
            name.casefold(),
            name,
            candidate.module_name,
            object_name,
            candidate.origin,
        )

    def _normalize_name_allowlist(
        self,
        name_allowlist: tuple[str, ...] | None,
    ) -> frozenset[str] | None:
        if name_allowlist is None:
            return None
        normalized: set[str] = set()
        for raw_name in name_allowlist:
            normalized.add(self._validate_name(raw_name))
        return frozenset(normalized)

    def _validate_group(self, group: str) -> str:
        cleaned = group.strip()
        if (
            not cleaned
            or len(cleaned) > 255
            or not all(segment.isidentifier() for segment in cleaned.split("."))
        ):
            raise ValueError("group must be a valid dotted identifier")
        return cleaned

    def _validate_name(self, name: str) -> str:
        cleaned = name.strip()
        allowed_punctuation = {"-", "_", "."}
        if (
            not cleaned
            or len(cleaned) > 128
            or any(
                not character.isalnum() and character not in allowed_punctuation
                for character in cleaned
            )
        ):
            raise ValueError("entry point name is invalid")
        return cleaned

    def _validate_module_name(self, module_name: str) -> None:
        if (
            not module_name
            or len(module_name) > 512
            or not all(segment.isidentifier() for segment in module_name.split("."))
        ):
            raise ValueError("entry point module name is invalid")

    def _validate_object_name(self, object_name: str | None) -> None:
        if object_name is None:
            return
        if (
            not object_name
            or len(object_name) > 512
            or not all(segment.isidentifier() for segment in object_name.split("."))
        ):
            raise ValueError("entry point object name is invalid")
