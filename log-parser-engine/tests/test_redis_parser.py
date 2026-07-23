from __future__ import annotations

from pathlib import Path

from log_parser_engine.core import ParserContext
from log_parser_engine.models import LogSeverity, LogSourceType, ParseStatus
from log_parser_engine.parsers import RedisLogParser


def test_redis_parser_metadata() -> None:
    parser = RedisLogParser()
    metadata = parser.metadata

    assert metadata.name == "redis_log"
    assert metadata.source_type == LogSourceType.REDIS
    assert metadata.supported_extensions == (".log", ".txt")
    assert metadata.supported_content_types == ("text/plain",)
    assert metadata.priority == 110
    assert metadata.enabled_by_default is True
    assert metadata.supports_multiline is False
    assert metadata.thread_safe is True
    assert "redis" in metadata.tags


def test_redis_parser_parses_server_log() -> None:
    parser = RedisLogParser()
    fixture = Path(__file__).parent / "fixtures" / "redis" / "server.log"

    result = parser.safe_parse(fixture.read_text(encoding="utf-8"))

    assert result.status == ParseStatus.success
    assert len(result.events) == 1
    event = result.events[0]
    assert event.source_type == LogSourceType.REDIS
    assert event.severity == LogSeverity.INFO
    assert event.event_type == "redis.lifecycle.ready"
    assert event.attributes["redis"]["role"] == "master"
    assert event.attributes["redis"]["role_code"] == "M"


def test_redis_parser_parses_sentinel_log() -> None:
    parser = RedisLogParser()
    fixture = Path(__file__).parent / "fixtures" / "redis" / "sentinel.log"

    result = parser.safe_parse(fixture.read_text(encoding="utf-8"))

    assert result.status == ParseStatus.success
    assert result.events[0].event_type == "redis.sentinel.subjective_down"


def test_redis_parser_parses_wrapped_systemd_log() -> None:
    parser = RedisLogParser()
    fixture = Path(__file__).parent / "fixtures" / "redis" / "wrapped_systemd.log"

    result = parser.safe_parse(fixture.read_text(encoding="utf-8"))

    assert result.status == ParseStatus.success
    assert result.events[0].attributes["redis"]["outer_host"] == "redis01"


def test_redis_parser_returns_failure_for_malformed_input() -> None:
    parser = RedisLogParser()
    fixture = Path(__file__).parent / "fixtures" / "redis" / "malformed.log"

    result = parser.safe_parse(fixture.read_text(encoding="utf-8"))

    assert result.status == ParseStatus.failed
    assert result.errors


def test_redis_parser_detects_redis_content() -> None:
    parser = RedisLogParser()
    result = parser.safe_detect("12345:M 23 Jul 2026 14:32:10.123 * Ready to accept connections")

    assert result.match is True
    assert result.confidence >= 0.6
