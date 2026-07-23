from __future__ import annotations

from pathlib import Path

from log_parser_engine.models import LogSeverity, LogSourceType, ParseStatus
from log_parser_engine.parsers.webserver import AccessLogParser, ErrorLogParser


FIXTURES = Path(__file__).parent / "fixtures" / "webserver"


def test_access_parser_parses_apache_combined_log() -> None:
    parser = AccessLogParser(vendor="apache")
    fixture = FIXTURES / "apache_combined.log"

    result = parser.safe_parse(fixture.read_text(encoding="utf-8"))

    assert result.status == ParseStatus.success
    assert len(result.events) == 1
    event = result.events[0]
    assert event.source_type == LogSourceType.APACHE
    assert event.http_status == 200
    assert event.http_method == "get"
    assert event.http_path == "/index.html"
    assert event.client_ip == "192.168.1.10"


def test_error_parser_parses_apache_error_log() -> None:
    parser = ErrorLogParser(vendor="apache")
    fixture = FIXTURES / "apache_error.log"

    result = parser.safe_parse(fixture.read_text(encoding="utf-8"))

    assert result.status == ParseStatus.success
    assert len(result.events) == 1
    event = result.events[0]
    assert event.source_type == LogSourceType.APACHE
    assert event.severity == LogSeverity.ERROR
    assert "client denied" in event.message.lower()


def test_nginx_access_detection_is_supported() -> None:
    parser = AccessLogParser(vendor="nginx")
    fixture = FIXTURES / "nginx_access.log"

    detection = parser.safe_detect(fixture.read_text(encoding="utf-8"))

    assert detection.match is True
    assert detection.confidence >= 0.6
