from __future__ import annotations

from datetime import datetime, timezone

import pytest

from log_parser_engine.core import BaseParser, ParserContext
from log_parser_engine.models import (
    DetectionResult,
    ErrorType,
    LogEvent,
    LogSeverity,
    LogSourceType,
    ParseResult,
    ParserMetadata,
    ParseStatus,
)


class SuccessfulTestParser(BaseParser):
    @property
    def metadata(self) -> ParserMetadata:
        return ParserMetadata(
            name="successful_test",
            display_name="Successful Test Parser",
            version="1.0.0",
            source_type=LogSourceType.application,
        )

    def detect(
        self,
        raw_log: str,
        context: ParserContext | None = None,
    ) -> DetectionResult:
        return DetectionResult.match("successful_test", 0.9, reason="ok")

    def parse(
        self,
        raw_log: str,
        context: ParserContext | None = None,
    ) -> ParseResult:
        event = LogEvent(
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            source_type=LogSourceType.application,
            message="ok",
            raw_message=raw_log,
            severity=LogSeverity.INFO,
        )
        return ParseResult(status=ParseStatus.success, events=[event])


class FailingDetectionParser(BaseParser):
    @property
    def metadata(self) -> ParserMetadata:
        return ParserMetadata(
            name="failing_detection",
            display_name="Failing Detection Parser",
            version="1.0.0",
            source_type=LogSourceType.application,
        )

    def detect(
        self,
        raw_log: str,
        context: ParserContext | None = None,
    ) -> DetectionResult:
        raise RuntimeError("boom")

    def parse(
        self,
        raw_log: str,
        context: ParserContext | None = None,
    ) -> ParseResult:
        raise AssertionError("not used")


class FailingParseParser(BaseParser):
    @property
    def metadata(self) -> ParserMetadata:
        return ParserMetadata(
            name="failing_parse",
            display_name="Failing Parse Parser",
            version="1.0.0",
            source_type=LogSourceType.application,
        )

    def detect(
        self,
        raw_log: str,
        context: ParserContext | None = None,
    ) -> DetectionResult:
        return DetectionResult.no_match("failing_parse")

    def parse(
        self,
        raw_log: str,
        context: ParserContext | None = None,
    ) -> ParseResult:
        raise RuntimeError("parse boom")


class InvalidDetectionReturnParser(BaseParser):
    @property
    def metadata(self) -> ParserMetadata:
        return ParserMetadata(
            name="invalid_detect",
            display_name="Invalid Detect Parser",
            version="1.0.0",
            source_type=LogSourceType.application,
        )

    def detect(
        self,
        raw_log: str,
        context: ParserContext | None = None,
    ) -> DetectionResult:
        return {"bad": "value"}  # type: ignore[return-value]

    def parse(
        self,
        raw_log: str,
        context: ParserContext | None = None,
    ) -> ParseResult:
        raise AssertionError("not used")


class InvalidParseReturnParser(BaseParser):
    @property
    def metadata(self) -> ParserMetadata:
        return ParserMetadata(
            name="invalid_parse",
            display_name="Invalid Parse Parser",
            version="1.0.0",
            source_type=LogSourceType.application,
        )

    def detect(
        self,
        raw_log: str,
        context: ParserContext | None = None,
    ) -> DetectionResult:
        return DetectionResult.no_match("invalid_parse")

    def parse(
        self,
        raw_log: str,
        context: ParserContext | None = None,
    ) -> ParseResult:
        return {"bad": "value"}  # type: ignore[return-value]


class MissingAbstractMethodsParser(BaseParser):
    @property
    def metadata(self) -> ParserMetadata:
        return ParserMetadata(
            name="missing",
            display_name="Missing Parser",
            version="1.0.0",
            source_type=LogSourceType.application,
        )


class MissingMetadataParser(BaseParser):
    def detect(
        self,
        raw_log: str,
        context: ParserContext | None = None,
    ) -> DetectionResult:
        return DetectionResult.no_match("missing")

    def parse(
        self,
        raw_log: str,
        context: ParserContext | None = None,
    ) -> ParseResult:
        return ParseResult(status=ParseStatus.failed)


def test_base_parser_cannot_be_instantiated() -> None:
    with pytest.raises(TypeError):
        BaseParser()  # type: ignore[abstract]


def test_concrete_parser_metadata_is_available() -> None:
    parser = SuccessfulTestParser()
    assert parser.name == "successful_test"
    assert parser.version == "1.0.0"
    assert parser.source_type == LogSourceType.application
    assert parser.is_enabled() is True


def test_safe_detect_returns_detection_result() -> None:
    parser = SuccessfulTestParser()
    result = parser.safe_detect("test")
    assert result.matched is True
    assert result.parser_name == "successful_test"


def test_safe_detect_returns_no_match_for_empty_input() -> None:
    parser = SuccessfulTestParser()
    assert parser.safe_detect("   ").matched is False


def test_safe_detect_handles_exception() -> None:
    parser = FailingDetectionParser()
    result = parser.safe_detect("test")
    assert result.matched is False
    assert "RuntimeError" in result.reason


def test_safe_detect_handles_invalid_return_type() -> None:
    parser = InvalidDetectionReturnParser()
    result = parser.safe_detect("test")
    assert result.matched is False


def test_safe_parse_returns_parse_result() -> None:
    parser = SuccessfulTestParser()
    result = parser.safe_parse("test")
    assert result.status == ParseStatus.success
    assert len(result.events) == 1


def test_safe_parse_returns_failure_for_empty_input() -> None:
    parser = SuccessfulTestParser()
    result = parser.safe_parse("   ")
    assert result.status == ParseStatus.failed
    assert result.errors[0].error_type == ErrorType.EMPTY_INPUT


def test_safe_parse_handles_exception() -> None:
    parser = FailingParseParser()
    result = parser.safe_parse("test")
    assert result.status == ParseStatus.failed
    assert result.errors[0].error_type == ErrorType.INTERNAL_ERROR


def test_safe_parse_handles_invalid_return_type() -> None:
    parser = InvalidParseReturnParser()
    result = parser.safe_parse("test")
    assert result.status == ParseStatus.failed


def test_truncate_raw_preserves_short_input() -> None:
    parser = SuccessfulTestParser()
    assert parser._truncate_raw("hello") == "hello"


def test_truncate_raw_handles_long_input() -> None:
    parser = SuccessfulTestParser()
    long_input = "x" * 600
    assert len(parser._truncate_raw(long_input)) < len(long_input)


def test_base_parser_cannot_be_instantiated_without_abstract_methods() -> None:
    with pytest.raises(TypeError):
        MissingAbstractMethodsParser()  # type: ignore[abstract]


def test_base_parser_cannot_be_instantiated_without_metadata() -> None:
    with pytest.raises(TypeError):
        MissingMetadataParser()  # type: ignore[abstract]
