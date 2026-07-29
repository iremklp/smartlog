from __future__ import annotations

from log_parser_engine.application import (
    ApplicationContainer,
    ApplicationOptions,
    LogAnalysisApplicationService,
)
from log_parser_engine.core import ParserRegistry
from log_parser_engine.models import LogSourceType
from log_parser_engine.storage import InMemoryEventStore
from tests.helpers.fake_parser import FakeParser


def test_runtime_statistics_reports_store_and_parser_counts() -> None:
    parser = FakeParser("fake", source_type=LogSourceType.FILE)
    registry = ParserRegistry([parser])
    container = ApplicationContainer.build(
        options=ApplicationOptions(enable_builtin_parsers=False),
        registry=registry,
        store=InMemoryEventStore(),
    )
    service = LogAnalysisApplicationService(container)

    stats = service.runtime_statistics()

    assert stats.parser_count == 1
    assert stats.enabled_parser_count == 1
    assert stats.store_statistics.event_count == 0
