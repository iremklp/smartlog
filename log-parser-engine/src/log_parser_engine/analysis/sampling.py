from __future__ import annotations

import hashlib
import heapq
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Generic, TypeVar

from log_parser_engine.exceptions.analysis import AnalysisSampleLimitError

T = TypeVar("T")


def deterministic_sample(
    values: Sequence[T],
    *,
    max_samples: int,
) -> tuple[T, ...]:
    """Select evenly spaced values without mutating input or using randomness."""
    if max_samples <= 0:
        raise ValueError("max_samples must be positive")
    size = len(values)
    if size <= max_samples:
        return tuple(values)
    return tuple(values[(index * size) // max_samples] for index in range(max_samples))


@dataclass(order=True, slots=True)
class _ReservoirEntry(Generic[T]):
    """One max-heap entry represented with reversed deterministic priority."""

    reversed_priority: int
    reversed_order: int
    value: T = field(compare=False)


class BoundedDeterministicSample(Generic[T]):
    """Collect exact samples up to a limit or a deterministic bounded reservoir.

    When sampling is enabled, the items with the smallest SHA-256 priorities are
    retained. Callers supply a stable key (normally an event id/content hash), so
    a repeated run over the same snapshot produces the same sample without random
    state. When sampling is disabled, the limit is checked before the next item is
    appended.
    """

    __slots__ = (
        "_allow_sampling",
        "_count",
        "_exact",
        "_heap",
        "_max_samples",
        "_order",
    )

    def __init__(self, *, max_samples: int, allow_sampling: bool) -> None:
        if max_samples <= 0:
            raise ValueError("max_samples must be positive")
        self._max_samples = max_samples
        self._allow_sampling = allow_sampling
        self._count = 0
        self._order = 0
        self._exact: list[T] = []
        self._heap: list[_ReservoirEntry[T]] = []

    @property
    def count(self) -> int:
        return self._count

    @property
    def sampled(self) -> bool:
        return self._allow_sampling and self._count > self._max_samples

    @property
    def retained_count(self) -> int:
        return len(self._heap) if self._allow_sampling else len(self._exact)

    def add(self, value: T, *, key: str) -> None:
        """Add one item without ever retaining more than ``max_samples``."""
        if not self._allow_sampling:
            if len(self._exact) >= self._max_samples:
                raise AnalysisSampleLimitError(
                    f"numeric sample count {self._count + 1} exceeds limit "
                    f"{self._max_samples}"
                )
            self._exact.append(value)
            self._count += 1
            return

        priority = int.from_bytes(
            hashlib.sha256(key.encode("utf-8", errors="surrogatepass")).digest(),
            byteorder="big",
            signed=False,
        )
        entry = _ReservoirEntry(
            reversed_priority=-priority,
            reversed_order=-self._order,
            value=value,
        )
        self._order += 1
        self._count += 1
        if len(self._heap) < self._max_samples:
            heapq.heappush(self._heap, entry)
            return
        worst = self._heap[0]
        if (entry.reversed_priority, entry.reversed_order) > (
            worst.reversed_priority,
            worst.reversed_order,
        ):
            heapq.heapreplace(self._heap, entry)

    def values(self) -> tuple[T, ...]:
        """Return retained values in deterministic priority/order sequence."""
        if not self._allow_sampling:
            return tuple(self._exact)
        ordered = sorted(
            self._heap,
            key=lambda item: (
                -item.reversed_priority,
                -item.reversed_order,
            ),
        )
        return tuple(item.value for item in ordered)
