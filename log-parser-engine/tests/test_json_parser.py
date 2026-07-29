from __future__ import annotations

from pathlib import Path

from log_parser_engine.core import ParserContext
from log_parser_engine.models import LogSeverity, LogSourceType, ParseStatus
from log_parser_engine.parsers import JsonLogParser


def test_json_parser_metadata() -> None:
    parser = JsonLogParser()
    metadata = parser.metadata
    assert metadata.name == "json_log"
    assert metadata.source_type == LogSourceType.JSON
    assert metadata.supported_extensions == (".json", ".jsonl", ".ndjson", ".log")
    assert metadata.supported_content_types[0] == "application/json"


def test_json_parser_parses_generic_json() -> None:
    parser = JsonLogParser()
    fixture = Path(__file__).parent / "fixtures" / "json" / "generic.json"

    result = parser.safe_parse(fixture.read_text(encoding="utf-8"))

    assert result.status == ParseStatus.success
    assert len(result.events) == 1
    event = result.events[0]
    assert event.source_type == LogSourceType.JSON
    assert event.severity == LogSeverity.INFO
    assert event.message == "Order created"
    assert event.service == "orders-api"


def test_json_parser_detects_json_content() -> None:
    parser = JsonLogParser()
    raw_log = '{"timestamp":"2026-07-23T14:32:10Z","message":"hello"}'
    result = parser.safe_detect(raw_log)
    assert result.match is True
    assert result.confidence >= 0.6


def test_json_parser_parses_json_lines_non_strict() -> None:
    parser = JsonLogParser()
    fixture = Path(__file__).parent / "fixtures" / "json" / "json_lines.log"

    result = parser.safe_parse(fixture.read_text(encoding="utf-8"))

    assert result.status == ParseStatus.success
    assert len(result.events) == 1
    event = result.events[0]
    assert event.message == "first"
    assert event.attributes["json_lines"]["additional_record_count"] == 1


def test_json_parser_fails_on_multiple_json_objects_in_strict_mode() -> None:
    parser = JsonLogParser()
    fixture = Path(__file__).parent / "fixtures" / "json" / "json_lines.log"

    context = ParserContext(strict=True)
    result = parser.safe_parse(fixture.read_text(encoding="utf-8"), context=context)

    assert result.status == ParseStatus.failed
    assert result.errors
