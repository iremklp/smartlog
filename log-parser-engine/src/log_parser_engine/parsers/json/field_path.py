from __future__ import annotations

from typing import Any


class FieldPathResolver:
    def __init__(self, field_paths: tuple[str, ...] | None = None) -> None:
        self.field_paths = tuple(path.strip() for path in (field_paths or ()) if path and str(path).strip())

    def resolve(self, data: dict[str, object]) -> Any:
        for path in self.field_paths:
            value = self._resolve_path(data, path)
            if value is not None:
                return value
        return None

    def _resolve_path(self, data: dict[str, object], path: str) -> Any:
        current: Any = data
        for part in path.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current
