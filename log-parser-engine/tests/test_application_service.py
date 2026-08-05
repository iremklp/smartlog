from __future__ import annotations

from datetime import datetime, timezone

from log_parser_engine.application import (
    ApplicationContainer,
    ApplicationOptions,
    LogAnalysisApplicationService,
    ParseBytesCommand,
    ParseTextCommand,
)
from log_parser_engine.core import ParserRegistry
from log_parser_engine.models import (
    BatchWriteResult,
    EventQuery,
    LogEvent,
    LogSeverity,
    LogSourceType,
    ParseResult,
)
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


def test_application_service_execute_parse_text_with_explicit_parser() -> None:
    service = build_service()

    result = service.execute_parse_text(
        ParseTextCommand(raw_log="hello world", parser_name="fake")
    ).result

    assert isinstance(result, ParseResult)
    assert result.status.value == "success"
    assert len(result.events) == 1


def test_application_service_execute_parse_bytes_batch_store() -> None:
    service = build_service()

    result = service.execute_parse_bytes(
        ParseBytesCommand(
            data=b"hello world\nhello world",
            file_name="sample.log",
            batch_mode=True,
            store_result=True,
        )
    ).result

    assert isinstance(result, BatchWriteResult)
    assert len(result.inserted) == 1
    assert service.store.count() == 1


def test_application_service_public_config_is_safe_and_bounded() -> None:
    options = ApplicationOptions(
        enable_builtin_parsers=False,
        max_upload_bytes=2048,
    )
    container = ApplicationContainer.build(
        options=options,
        registry=ParserRegistry(),
        store=InMemoryEventStore(),
    )
    service = LogAnalysisApplicationService(container)

    config = service.public_config()

    assert config.app.name == "log-parser-engine"
    assert config.limits.max_upload_bytes == 2048
    assert config.capabilities.supports_file_upload is True
    assert config.capabilities.uses_persistent_storage is False
