from __future__ import annotations

import importlib
from collections.abc import Iterable
from typing import Any

from log_parser_engine.exceptions import PluginLoadError
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

    def __init__(self, *, group: str = "log_parser_engine.parsers") -> None:
        cleaned_group = group.strip()
        if not cleaned_group:
            raise ValueError("group must not be empty")
        self._group = cleaned_group

    @property
    def source_name(self) -> str:
        return "entry_point"

    def discover(self) -> tuple[PluginCandidate, ...]:
        entry_points = importlib.metadata.entry_points()
        matches = _entry_point_matches(entry_points, self._group)

        candidates: list[PluginCandidate] = []
        for entry_point in matches:
            candidates.append(
                PluginCandidate(
                    name=str(getattr(entry_point, "name", "")),
                    source="entry_point",
                    module_name=str(getattr(entry_point, "module", "")),
                    object_name=getattr(entry_point, "attr", None),
                    entry_point_group=self._group,
                    entry_point_name=str(getattr(entry_point, "name", "")),
                    origin=(
                        f"entry_point:{self._group}:"
                        f"{getattr(entry_point, 'name', '')}"
                    ),
                )
            )
        return tuple(sorted(candidates, key=lambda candidate: candidate.origin))

    def load(self, candidate: PluginCandidate) -> object:
        if candidate.source != "entry_point":
            raise PluginLoadError("candidate source is not entry_point")

        entry_points = importlib.metadata.entry_points()
        matches = _entry_point_matches(
            entry_points,
            candidate.entry_point_group or self._group,
        )

        for entry_point in matches:
            entry_point_obj = entry_point
            if not hasattr(entry_point_obj, "name"):
                continue
            if (
                getattr(entry_point_obj, "name", None) == candidate.entry_point_name
                and getattr(entry_point_obj, "module", None) == candidate.module_name
                and getattr(entry_point_obj, "attr", None) == candidate.object_name
            ):
                load_method = getattr(entry_point_obj, "load", None)
                if not callable(load_method):
                    raise PluginLoadError("entry point is not callable")
                loaded = load_method()
                return resolve_parser_instance(loaded)

        raise PluginLoadError(f"entry point {candidate.qualified_name} was not found")
