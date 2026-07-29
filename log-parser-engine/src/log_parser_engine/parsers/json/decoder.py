from __future__ import annotations

import json
from typing import Any

from log_parser_engine.exceptions import JsonDecodingError, JsonStructureError


class _DuplicateAwareDict(dict):
    def __init__(
        self,
        pairs: list[tuple[str, Any]],
        *,
        strict_duplicates: bool = False,
    ) -> None:
        super().__init__()
        self.duplicates: tuple[str, ...] = ()
        seen: set[str] = set()
        duplicates: list[str] = []
        for key, value in pairs:
            if key in seen:
                duplicates.append(key)
            else:
                seen.add(key)
            self[key] = value
        self.duplicates = tuple(duplicates)
        if strict_duplicates and self.duplicates:
            raise JsonStructureError("duplicate JSON keys detected")


def decode_json_value(
    raw_json: str,
    *,
    strict_duplicates: bool = False,
) -> tuple[object, tuple[str, ...]]:
    if not isinstance(raw_json, str):
        raise JsonDecodingError("input must be a string")
    if not raw_json.strip():
        raise JsonDecodingError("input must not be empty")

    try:
        parsed = json.loads(
            raw_json,
            object_pairs_hook=_build_pairs_hook(strict_duplicates),
        )
    except json.JSONDecodeError as exc:
        raise JsonDecodingError(f"invalid JSON: {exc.msg}") from exc

    if strict_duplicates and getattr(parsed, "duplicates", None):
        raise JsonStructureError("duplicate JSON keys detected")

    if isinstance(parsed, dict):
        return parsed, tuple(getattr(parsed, "duplicates", ()) or ())
    if isinstance(parsed, (list, tuple)):
        raise JsonStructureError("top-level JSON array is not supported")
    raise JsonStructureError("top-level JSON value must be an object")


def decode_json_object(
    raw_json: str,
    *,
    strict_duplicates: bool = False,
) -> dict[str, object]:
    parsed, _ = decode_json_value(raw_json, strict_duplicates=strict_duplicates)
    if not isinstance(parsed, dict):
        raise JsonStructureError("top-level JSON value must be an object")
    return dict(parsed)


def _build_pairs_hook(strict_duplicates: bool) -> Any:
    def hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        return _DuplicateAwareDict(pairs, strict_duplicates=strict_duplicates)

    return hook
