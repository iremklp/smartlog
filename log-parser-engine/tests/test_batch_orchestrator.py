from __future__ import annotations

from datetime import datetime, timezone

from log_parser_engine.batch import BatchParseOptions, BatchParseOrchestrator
from log_parser_engine.core import (
    BaseParser,
    ParserContext,
    ParserManager,
    ParserRegistry,
)
from log_parser_engine.models import (
    DetectionResult,
    ErrorType,
    LogEvent,
    LogSourceType,
    ParseError,
    ParseResult,
    ParserMetadata,
    ParseStatus,
)


class PrefixParser(BaseParser):
    def __init__(self, name: str, prefix: str) -> None:
        super().__init__()
        self._name = name
        self._prefix = prefix

    @property
    def metadata(self) -> ParserMetadata:
        return ParserMetadata(
            name=self._name,
            display_name=self._name,
            version="1.0.0",
            source_type=LogSourceType.application,
            supports_multiline=False,
            supports_batch=False,
        )

    def detect(
        self, raw_log: str, context: ParserContext | None = None
    ) -> DetectionResult:
        if any(
            line.startswith(self._prefix)
            for line in raw_log.splitlines()
            if line.strip()
        ):
            return DetectionResult.match(self._name, 0.95, reason="prefix")
        return DetectionResult.no_match(self._name, reason="no prefix")

    def parse(self, raw_log: str, context: ParserContext | None = None) -> ParseResult:
        if "BAD" in raw_log:
            return ParseResult(
                status=ParseStatus.failed,
                errors=[
                    ParseError(
                        message="bad record",
                        error_type=ErrorType.PARSE_FAILED,
                        status=ParseStatus.failed,
                    )
                ],
            )
        event = LogEvent(
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            source_type=LogSourceType.application,
            message=raw_log,
            raw_message=raw_log,
        )
        return ParseResult(status=ParseStatus.success, events=[event])


def _orchestrator() -> BatchParseOrchestrator:
    registry = ParserRegistry([PrefixParser("alpha", "A:"), PrefixParser("beta", "B:")])
    manager = ParserManager(registry)
    return BatchParseOrchestrator(manager)


def test_orchestrator_parse_lines_detect_once() -> None:
    orchestrator = _orchestrator()
    result = orchestrator.parse_lines(
        ["A: one\n", "A: two\n"], options=BatchParseOptions()
    )
    assert result.statistics.records_succeeded == 2
    assert result.statistics.parser_detection_count == 1
    assert len(result.events) == 2


def test_orchestrator_collects_failures() -> None:
    orchestrator = _orchestrator()
    result = orchestrator.parse_lines(
        ["A: one\n", "A: BAD\n", "A: three\n"], options=BatchParseOptions()
    )
    assert result.statistics.records_failed == 1
    assert len(result.failures) == 1


def test_orchestrator_progress_callback() -> None:
    orchestrator = _orchestrator()
    seen: list[int] = []

    stream = orchestrator.iter_parse_lines(
        ["A: one\n", "A: two\n"],
        options=BatchParseOptions(progress_interval_records=1),
        progress_callback=lambda p: seen.append(p.records_seen),
    )
    list(stream)
    assert seen[-1] >= 2
