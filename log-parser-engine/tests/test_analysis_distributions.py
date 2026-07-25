from __future__ import annotations

from datetime import datetime, timezone

import pytest

from log_parser_engine.analysis.distributions import (
    build_distribution,
    build_distributions,
)
from log_parser_engine.analysis.options import AnalysisOptions
from log_parser_engine.exceptions.analysis import (
    AnalysisFieldResolutionError,
    AnalysisGroupLimitError,
)
from log_parser_engine.models.enums import LogSeverity, LogSourceType
from log_parser_engine.models.log_event import LogEvent
from log_parser_engine.models.stored_event import StoredEvent


def make_event(index: int, **updates: object) -> StoredEvent:
    values: dict[str, object] = {
        "timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "source_type": LogSourceType.APPLICATION,
        "severity": LogSeverity.INFO,
        "message": f"event {index}",
        "raw_message": f"event {index}",
    }
    values.update(updates)
    return StoredEvent(
        id=f"evt-{index}",
        event=LogEvent(**values),
        inserted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        sequence=index + 1,
        content_hash=f"{index + 1:064x}",
        estimated_size_bytes=100,
    )


def test_scalar_distribution_missing_top_n_and_stable_ties() -> None:
    events = (
        make_event(0, service="beta"),
        make_event(1, service="alpha"),
        make_event(2, service="beta"),
        make_event(3),
        make_event(4, service="alpha"),
        make_event(5, service="gamma"),
    )
    result = build_distribution(events, field="service", top_n=2)
    assert result.total_count == 6
    assert result.matched_value_count == 5
    assert result.missing_count == 1
    assert result.unique_value_count == 3
    assert [item.key for item in result.items] == ["alpha", "beta"]
    assert [item.percentage for item in result.items] == pytest.approx(
        [100 / 3, 100 / 3]
    )
    assert result.other_count == 1
    assert result.truncated


def test_tags_are_multi_valued_and_deduplicated_per_event() -> None:
    events = (
        make_event(0, tags=["prod", "api", "prod"]),
        make_event(1, tags=["prod"]),
        make_event(2),
    )
    result = build_distribution(events, field="tags", top_n=10)
    assert result.matched_value_count == 3
    assert result.missing_count == 1
    assert [(item.key, item.count) for item in result.items] == [
        ("prod", 2),
        ("api", 1),
    ]


def test_http_and_custom_scalar_distributions() -> None:
    events = (
        make_event(
            0,
            http_status=200,
            http_method="get",
            attributes={"tenant": {"name": "blue"}},
        ),
        make_event(
            1,
            http_status=503,
            http_method="POST",
            attributes={"tenant": {"name": "green"}},
        ),
        make_event(2, attributes={"tenant": {"name": {"complex": True}}}),
    )
    results = build_distributions(
        events,
        fields=("status_class", "http_method", "tenant.name"),
        top_n=10,
    )
    assert [(item.key, item.count) for item in results[0].items] == [
        ("2xx", 1),
        ("5xx", 1),
    ]
    assert [item.key for item in results[1].items] == ["GET", "POST"]
    assert [item.key for item in results[2].items] == ["blue", "green"]
    assert results[2].missing_count == 1


def test_exact_group_limit_is_enforced() -> None:
    events = tuple(make_event(index, service=f"service-{index}") for index in range(3))
    with pytest.raises(AnalysisGroupLimitError):
        build_distribution(
            events,
            field="service",
            top_n=2,
            options=AnalysisOptions(max_groups=2),
        )


def test_distribution_does_not_mutate_events() -> None:
    events = (make_event(0, service="api"),)
    before = events[0].model_dump()
    build_distribution(events, field="service", top_n=10)
    assert events[0].model_dump() == before


@pytest.mark.parametrize("field", ["raw_message", "message", "__class__"])
def test_unsafe_or_raw_content_grouping_is_rejected(field: str) -> None:
    with pytest.raises(AnalysisFieldResolutionError):
        build_distribution((make_event(0),), field=field, top_n=10)
