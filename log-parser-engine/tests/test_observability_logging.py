from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from log_parser_engine.api import create_app
from log_parser_engine.application import (
    AnalyzeEventsCommand,
    ApplicationContainer,
    ApplicationOptions,
    LogAnalysisApplicationService,
    ParseTextCommand,
)
from log_parser_engine.core import ParserRegistry
from log_parser_engine.models import LogEvent, LogSeverity, LogSourceType
from log_parser_engine.observability.context import (
    operation_id_context,
    request_id_context,
)
from log_parser_engine.observability.logging import (
    JsonLogFormatter,
    configure_structured_logging,
    emit_structured_log,
)
from log_parser_engine.storage import InMemoryEventStore
from tests.helpers.fake_parser import FakeParser


def test_emit_structured_log_redacts_sensitive_fields_and_keeps_safe_counts() -> None:
    logger = logging.getLogger("log_parser_engine.test.redaction")
    records: list[dict[str, object]] = []

    class CaptureHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            if isinstance(record.msg, dict):
                records.append(record.msg)

    handler = CaptureHandler()
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    request_token = request_id_context.set("request-42")
    operation_token = operation_id_context.set("operation-42")
    try:
        emit_structured_log(
            logger,
            event="test.event",
            route="/api/v1/query",
            status_code=200,
            raw_log="secret-raw",
            upload_bytes=2048,
            metadata={"sensitive": "value"},
            search_text="needle",
            facet_fields=["severity", "service"],
        )
    finally:
        operation_id_context.reset(operation_token)
        request_id_context.reset(request_token)

    payload = records[-1]
    serialized = json.dumps(payload)
    assert payload["request_id"] == "request-42"
    assert payload["operation_id"] == "operation-42"
    assert payload["raw_log"] == "[REDACTED]"
    assert payload["metadata"] == "[REDACTED]"
    assert payload["search_text"] == "[REDACTED]"
    assert payload["facet_fields_count"] == 2
    assert "secret-raw" not in serialized
    assert "needle" not in serialized


def test_configure_structured_logging_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("LOG_PARSER_LOG_FORMAT", "json")
    monkeypatch.setenv("LOG_PARSER_LOG_LEVEL", "WARNING")
    monkeypatch.setenv("LOG_PARSER_DISABLE_UVICORN_ACCESS_LOG", "true")

    configure_structured_logging(force=True)

    logger = logging.getLogger("log_parser_engine")
    assert logger.level == logging.WARNING
    assert isinstance(logger.handlers[0].formatter, JsonLogFormatter)
    assert logging.getLogger("uvicorn.access").disabled is True

    monkeypatch.setenv("LOG_PARSER_LOG_FORMAT", "plain")
    monkeypatch.setenv("LOG_PARSER_DISABLE_UVICORN_ACCESS_LOG", "false")

    configure_structured_logging(force=True)

    logger = logging.getLogger("log_parser_engine")
    assert not isinstance(logger.handlers[0].formatter, JsonLogFormatter)
    assert logging.getLogger("uvicorn.access").disabled is False


def test_runtime_statistics_include_request_and_slow_request_metrics(
    monkeypatch,
) -> None:
    ticks = iter((0.0, 0.01, 0.02, 0.03))
    monkeypatch.setattr(
        "log_parser_engine.api.middleware.perf_counter",
        lambda: next(ticks),
    )
    options = ApplicationOptions(
        enable_builtin_parsers=False,
        slow_request_threshold_ms=1.0,
    )
    container = ApplicationContainer.build(
        options=options,
        registry=ParserRegistry([]),
        store=InMemoryEventStore(),
    )
    client = TestClient(create_app(container=container))

    first = client.get("/health")
    second = client.get("/api/v1/runtime/statistics")

    assert first.status_code == 200
    assert second.status_code == 200
    payload = second.json()
    assert payload["requests_total"] >= 1
    assert payload["slow_requests_total"] >= 1
    assert payload["average_request_duration_ms"] >= 0.0
    assert payload["maximum_request_duration_ms"] >= 0.0


def test_service_operation_logs_use_standard_events_without_raw_content(
    monkeypatch,
) -> None:
    parser = FakeParser("fake", source_type=LogSourceType.FILE)
    container = ApplicationContainer.build(
        options=ApplicationOptions(enable_builtin_parsers=False),
        registry=ParserRegistry([parser]),
        store=InMemoryEventStore(),
    )
    service = LogAnalysisApplicationService(container)

    records: list[dict[str, object]] = []

    def capture(
        _logger: logging.Logger,
        *,
        event: str,
        level: int = logging.INFO,
        **fields: object,
    ) -> None:
        records.append({"event": event, "level": level, **fields})

    monkeypatch.setattr(
        "log_parser_engine.application.service.emit_structured_log",
        capture,
    )
    monkeypatch.setattr(
        "log_parser_engine.application.service.emit_structured_log_fields",
        lambda _logger, *, event, fields, level=logging.INFO: records.append(
            {"event": event, "level": level, **fields}
        ),
    )

    service.execute_parse_text(ParseTextCommand(raw_log="secret-raw-line"))
    service.add_event(
        LogEvent(
            timestamp=datetime(2026, 8, 6, 10, 0, tzinfo=timezone.utc),
            source_type=LogSourceType.APPLICATION,
            severity=LogSeverity.INFO,
            message="safe message",
            raw_message="raw payload should not be logged",
        )
    )
    service.query_events()
    service.analyze_events(AnalyzeEventsCommand())

    events = {(item["event"], item.get("operation")) for item in records}
    assert ("operation.started", "parse_text") in events
    assert ("operation.completed", "parse_text") in events
    assert ("operation.started", "store_add_event") in events
    assert ("operation.completed", "store_add_event") in events
    assert ("operation.started", "query_events") in events
    assert ("operation.completed", "query_events") in events
    assert ("operation.started", "analyze_events") in events
    assert ("operation.completed", "analyze_events") in events

    serialized = json.dumps(records)
    assert "secret-raw-line" not in serialized
    assert "raw payload should not be logged" not in serialized
