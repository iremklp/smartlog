from __future__ import annotations

from dataclasses import dataclass, field

from .record_reader import SourceRecord


@dataclass(slots=True)
class DetectionSampleBuffer:
    """Bounded buffer for parser detection samples."""

    max_records: int
    max_characters: int
    _items: list[SourceRecord] = field(default_factory=list)
    _characters: int = 0

    def add(self, item: SourceRecord) -> bool:
        if self.full:
            return False
        if item.raw is None:
            return False
        if not item.raw.strip():
            return False
        if self.max_records <= len(self._items):
            return False
        if self._characters + item.character_count > self.max_characters and self._items:
            return False
        self._items.append(item)
        self._characters += item.character_count
        return True

    @property
    def full(self) -> bool:
        return len(self._items) >= self.max_records or self._characters >= self.max_characters

    @property
    def item_count(self) -> int:
        return len(self._items)

    def build_sample(self) -> str:
        return "\n".join(item.raw for item in self._items if item.raw is not None)

    def drain(self) -> tuple[SourceRecord, ...]:
        return tuple(self._items)
