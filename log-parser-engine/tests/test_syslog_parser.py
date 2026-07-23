from __future__ import annotations

from pathlib import Path

from log_parser_engine.core import ParserRegistry
from log_parser_engine.models import LogSeverity, LogSourceType, ParseStatus
from log_parser_engine.parsers import Rfc3164SyslogParser, Rfc5424SyslogParser
from log_parser_engine.plugins.package_loader import PackagePluginLoader
from log_parser_engine.plugins.plugin_discovery import PluginDiscovery


def test_syslog_parsers_metadata() -> None:
    rfc5424 = Rfc5424SyslogParser()
    rfc3164 = Rfc3164SyslogParser()

    assert rfc5424.metadata.source_type == LogSourceType.SYSLOG
    assert rfc3164.metadata.source_type == LogSourceType.SYSLOG
    assert rfc5424.metadata.name == "rfc5424_syslog"
    assert rfc3164.metadata.name == "rfc3164_syslog"


def test_rfc5424_syslog_parser_parses_fixture() -> None:
    parser = Rfc5424SyslogParser()
    fixture = Path(__file__).parent / "fixtures" / "syslog" / "rfc5424.log"

    result = parser.safe_parse(fixture.read_text(encoding="utf-8"))

    assert result.status == ParseStatus.success
    event = result.events[0]
    assert event.source_type == LogSourceType.SYSLOG
    assert event.severity == LogSeverity.CRITICAL
    assert event.event_type == "syslog.id47"
    assert event.host == "web01"
    assert event.application == "appname"
    assert event.attributes["syslog"]["format"] == "rfc5424"
    assert event.attributes["syslog"]["message_id"] == "ID47"


def test_rfc3164_syslog_parser_parses_fixture() -> None:
    parser = Rfc3164SyslogParser()
    fixture = Path(__file__).parent / "fixtures" / "syslog" / "rfc3164.log"

    result = parser.safe_parse(fixture.read_text(encoding="utf-8"))

    assert result.status == ParseStatus.success
    event = result.events[0]
    assert event.source_type == LogSourceType.SYSLOG
    assert event.severity == LogSeverity.NOTICE
    assert event.host == "web01"
    assert event.application == "su[1234]"
    assert event.attributes["syslog"]["format"] == "rfc3164"
    assert event.attributes["syslog"]["process_id"] == "1234"


def test_rfc5424_syslog_parser_detects_content() -> None:
    parser = Rfc5424SyslogParser()
    fixture = Path(__file__).parent / "fixtures" / "syslog" / "rfc5424.log"

    result = parser.safe_detect(fixture.read_text(encoding="utf-8"))

    assert result.match is True
    assert result.confidence >= 0.9


def test_rfc3164_syslog_parser_detects_content() -> None:
    parser = Rfc3164SyslogParser()
    fixture = Path(__file__).parent / "fixtures" / "syslog" / "rfc3164.log"

    result = parser.safe_detect(fixture.read_text(encoding="utf-8"))

    assert result.match is True
    assert result.confidence >= 0.8


def test_syslog_package_loader_discovers_both_plugins() -> None:
    loader = PackagePluginLoader("log_parser_engine.parsers.syslog")

    candidates = loader.discover()
    module_names = [candidate.module_name for candidate in candidates]

    assert module_names == [
        "log_parser_engine.parsers.syslog.rfc3164_plugin",
        "log_parser_engine.parsers.syslog.rfc5424_plugin",
    ]


def test_syslog_plugin_discovery_registers_two_parsers() -> None:
    loader = PackagePluginLoader("log_parser_engine.parsers.syslog")
    registry = ParserRegistry()

    result = PluginDiscovery(loaders=[loader]).discover_and_register(registry=registry)

    assert result.discovered_count == 2
    assert result.loaded_count == 2
    assert result.registered_count == 2
    assert result.failed_count == 0
    assert {item.name for item in registry.list_parsers()} == {
        "rfc3164_syslog",
        "rfc5424_syslog",
    }


def test_syslog_parser_returns_failure_for_malformed_input() -> None:
    parser = Rfc5424SyslogParser()
    fixture = Path(__file__).parent / "fixtures" / "syslog" / "malformed.log"

    result = parser.safe_parse(fixture.read_text(encoding="utf-8"))

    assert result.status == ParseStatus.failed
    assert result.errors