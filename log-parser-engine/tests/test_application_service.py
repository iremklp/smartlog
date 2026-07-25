from __future__ import annotations

from datetime import datetime, timezone

from log_parser_engine.application import ApplicationContainer, ApplicationOptions, LogAnalysisApplicationService
from log_parser_engine.core import ParserRegistry
from log_parser_engine.models import EventQuery, LogEvent, LogSeverity, LogSourceType
from log_parser_engine.storage import InMemoryEventStore
from tests.helpers.fake_parser import FakeParser


def build_service() -> LogAnalysisApplicationService:
    parser = FakeParser(
        "fake",
        source_type=LogSourceType.FILE,
        matched=True,
        confidence=0.9,
        reason="match",
    )
    registry = ParserRegistry([parser])
    container = ApplicationContainer.build(
        options=ApplicationOptions(enable_builtin_parsers=False),
        registry=registry,
        store=InMemoryEventStore(),
    )
    return LogAnalysisApplicationService(container)


def test_application_service_parses_and_stores_events() -> None:
    service = build_service()

    parse_result = service.parse_text("hello world")
    assert parse_result.success is True
    assert parse_result.event is not None

    write_result = service.parse_and_store_text("hello world")
    assert write_result.status == "inserted"
    assert service.store.count() == 1


def test_application_service_supports_queries() -> None:
    service = build_service()
    event = LogEvent(
        timestamp=datetime.now(timezone.utc),
        source_type=LogSourceType.FILE,
        message="stored",
        raw_message="stored",
        severity=LogSeverity.INFO,
    )
    service.add_event(event)

    result = service.query_events(EventQuery())
    assert result.page.total == 1
    assert result.events[0].event.message == "stored"