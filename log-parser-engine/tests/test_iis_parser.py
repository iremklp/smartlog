from __future__ import annotations

from pathlib import Path

from log_parser_engine.core import ParserContext
from log_parser_engine.models import LogSeverity, LogSourceType, ParseStatus
from log_parser_engine.parsers import IisW3CParser


def test_iis_parser_metadata() -> None:
    parser = IisW3CParser()
    metadata = parser.metadata

    assert metadata.name == "iis_w3c"
    assert metadata.source_type == LogSourceType.IIS
    assert metadata.supported_extensions == (".log",)
    assert metadata.supported_content_types == ("text/plain",)
    assert metadata.enabled_by_default is True
    assert metadata.supports_multiline is True
    assert metadata.supports_batch is False
    assert metadata.thread_safe is True
    assert "iis" in metadata.tags


def test_iis_parser_parses_header_and_data() -> None:
    parser = IisW3CParser()
    fixture = Path(__file__).parent / "fixtures" / "iis" / "standard.log"

    result = parser.safe_parse(fixture.read_text(encoding="utf-8"))

    assert result.status == ParseStatus.success
    assert len(result.events) == 1
    event = result.events[0]
    assert event.source_type == LogSourceType.IIS
    assert event.http_method == "GET"
    assert event.http_path == "/api/orders"
    assert event.http_status == 200
    assert event.client_ip == "10.1.2.3"
    assert event.server_ip == "10.0.0.10"
    assert event.severity == LogSeverity.INFO
    assert event.attributes["iis"]["substatus"] == 0
    assert event.attributes["iis"]["win32_status"] == 0


def test_iis_parser_parses_context_fields() -> None:
    parser = IisW3CParser()
    context = ParserContext(
        attributes={
            "iis_fields": ("date", "time", "cs-method", "cs-uri-stem", "sc-status")
        }
    )

    result = parser.safe_parse("2026-07-23 12:00:01 GET /health 200", context=context)

    assert result.status == ParseStatus.success
    assert result.events[0].http_method == "GET"
    assert result.events[0].http_path == "/health"
    assert result.events[0].http_status == 200


def test_iis_parser_returns_failure_for_malformed_input() -> None:
    parser = IisW3CParser()
    fixture = Path(__file__).parent / "fixtures" / "iis" / "malformed.log"

    result = parser.safe_parse(fixture.read_text(encoding="utf-8"))

    assert result.status == ParseStatus.failed
    assert result.errors
