from __future__ import annotations

from collections.abc import Mapping

from log_parser_engine.models.ranked_item import RankedItem

from .helpers import safe_ratio


def ranked_items(
    counts: Mapping[str, int],
    *,
    total_count: int,
    top_n: int,
    metric_values: Mapping[str, float | None] | None = None,
    metric_unit: str | None = None,
    attributes: Mapping[str, Mapping[str, object]] | None = None,
) -> tuple[tuple[RankedItem, ...], int, bool]:
    """Build a deterministic top-N ranking and exact other count."""
    if total_count < 0:
        raise ValueError("total_count must not be negative")
    if top_n <= 0:
        raise ValueError("top_n must be positive")
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    visible = ordered[:top_n]
    other_count = sum(count for _, count in ordered[top_n:])
    items = tuple(
        RankedItem(
            rank=index,
            key=key,
            display_value=key,
            count=count,
            percentage=safe_ratio(count, total_count) * 100.0,
            metric_value=metric_values.get(key) if metric_values else None,
            metric_unit=metric_unit,
            attributes=dict(attributes.get(key, {})) if attributes else {},
        )
        for index, (key, count) in enumerate(visible, start=1)
    )
    return items, other_count, len(ordered) > top_n
