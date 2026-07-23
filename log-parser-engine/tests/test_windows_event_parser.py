from __future__ import annotations

from pathlib import Path

from log_parser_engine.models import LogSeverity, LogSourceType, ParseStatus
from log_parser_engine.parsers import WindowsEventXmlParser


def test_windows_event_parser_metadata() -> None:
    parser = WindowsEventXmlParser()
    metadata = parser.metadata

    assert metadata.name == "windows_event_xml"
    assert metadata.source_type == LogSourceType.WINDOWS_EVENT
    assert metadata.supported_extensions == (".xml", ".evtx.xml", ".log")
    assert metadata.supported_content_types == (
        "application/xml",
        "text/xml",
        "text/plain",
    )
    assert metadata.supports_multiline is True
    assert metadata.supports_batch is False
    assert "windows" in metadata.tags


def test_windows_event_parser_parses_security_event() -> None:
    parser = WindowsEventXmlParser()
    fixture = (
        Path(__file__).parent
        / "fixtures"
        / "windows_event"
        / "security_event.xml"
    )

    result = parser.safe_parse(fixture.read_text(encoding="utf-8"))

    assert result.status == ParseStatus.success
    assert len(result.events) == 1
    event = result.events[0]
    assert event.source_type == LogSourceType.WINDOWS_EVENT
    assert event.severity == LogSeverity.INFO
    assert event.event_type == "windows.event.4624"
    assert event.host == "server01.contoso.local"
    assert event.service == "Microsoft-Windows-Security-Auditing"
    assert event.attributes["windows_event"]["event_id"] == 4624
    assert event.attributes["windows_event"]["event_data"]["TargetUserName"] == "jdoe"


def test_windows_event_parser_detects_xml_content() -> None:
    parser = WindowsEventXmlParser()
    fixture = (
        Path(__file__).parent
        / "fixtures"
        / "windows_event"
        / "security_event.xml"
    )

    result = parser.safe_detect(fixture.read_text(encoding="utf-8"))

    assert result.match is True
    assert result.confidence >= 0.8


def test_windows_event_parser_returns_failure_for_malformed_input() -> None:
    parser = WindowsEventXmlParser()
    fixture = Path(__file__).parent / "fixtures" / "windows_event" / "malformed.xml"

    result = parser.safe_parse(fixture.read_text(encoding="utf-8"))

    assert result.status == ParseStatus.failed
    assert result.errors