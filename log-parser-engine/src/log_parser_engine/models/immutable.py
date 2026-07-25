"""Small JSON-friendly immutable collection helpers for domain models."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, NoReturn, TypeVar, overload

_KeyT = TypeVar("_KeyT")
_ValueT = TypeVar("_ValueT")
_DefaultT = TypeVar("_DefaultT")
_ItemT = TypeVar("_ItemT")


class FrozenDict(dict[_KeyT, _ValueT]):
    """A ``dict``-compatible mapping that rejects every mutation operation.

    Subclassing ``dict`` keeps Pydantic and JSON serialization predictable
    while closing the shallow-immutability gap left by frozen Pydantic models.
    """

    @staticmethod
    def _immutable() -> NoReturn:
        raise TypeError("FrozenDict does not support mutation")

    def __setitem__(self, key: _KeyT, value: _ValueT) -> None:
        self._immutable()

    def __delitem__(self, key: _KeyT) -> None:
        self._immutable()

    def clear(self) -> None:
        self._immutable()

    @overload
    def pop(self, key: _KeyT) -> _ValueT: ...

    @overload
    def pop(self, key: _KeyT, default: _ValueT) -> _ValueT: ...

    @overload
    def pop(self, key: _KeyT, default: _DefaultT) -> _ValueT | _DefaultT: ...

    def pop(self, key: _KeyT, default: object = None) -> Any:
        self._immutable()

    def popitem(self) -> tuple[_KeyT, _ValueT]:
        self._immutable()

    def setdefault(
        self,
        key: _KeyT,
        default: _ValueT | None = None,
    ) -> _ValueT:
        self._immutable()

    def update(self, *args: Any, **kwargs: Any) -> None:
        self._immutable()

    def _immutable_operation(self, *args: object, **kwargs: object) -> NoReturn:
        self._immutable()

    def copy(self) -> FrozenDict[_KeyT, _ValueT]:
        """Return the same instance because the mapping cannot change."""

        return self

    def __copy__(self) -> FrozenDict[_KeyT, _ValueT]:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> FrozenDict[_KeyT, _ValueT]:
        return self


# ``dict.__ior__`` mutates at C level without calling ``__setitem__``. Installing
# the guard dynamically avoids a false mypy special-method compatibility error
# while retaining the exact runtime safety expected from this dict subclass.
setattr(FrozenDict, "__ior__", FrozenDict._immutable_operation)


class FrozenList(list[_ItemT]):
    """A JSON-friendly list that preserves list equality but cannot mutate."""

    @staticmethod
    def _immutable() -> NoReturn:
        raise TypeError("FrozenList does not support mutation")

    def _immutable_operation(self, *args: object, **kwargs: object) -> NoReturn:
        self._immutable()

    def copy(self) -> FrozenList[_ItemT]:
        return self

    def __copy__(self) -> FrozenList[_ItemT]:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> FrozenList[_ItemT]:
        return self


for _mutation_method in (
    "__delitem__",
    "__iadd__",
    "__imul__",
    "__setitem__",
    "append",
    "clear",
    "extend",
    "insert",
    "pop",
    "remove",
    "reverse",
    "sort",
):
    setattr(FrozenList, _mutation_method, FrozenList._immutable_operation)


def deep_freeze(value: Any) -> Any:
    """Recursively freeze JSON-like mappings and sequences."""

    if isinstance(value, Mapping):
        return FrozenDict(
            {
                key: deep_freeze(item)
                for key, item in value.items()
            }
        )
    if isinstance(value, (list, tuple)):
        return tuple(deep_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(deep_freeze(item) for item in value)
    return value


def freeze_mapping(
    value: Mapping[_KeyT, _ValueT],
) -> FrozenDict[_KeyT, Any]:
    """Return a recursively immutable, serialization-friendly mapping."""

    frozen = deep_freeze(value)
    if not isinstance(frozen, FrozenDict):  # pragma: no cover - mapping invariant
        raise TypeError("expected a mapping")
    return frozen
