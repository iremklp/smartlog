from __future__ import annotations

from datetime import datetime, timezone

from log_parser_engine.core import BaseParser, ParserContext
from log_parser_engine.models import (
    DetectionResult,
    LogEvent,
    LogSeverity,
    LogSourceType,
    ParseResult,
    ParserMetadata,
    ParseStatus,
)


class FakeParser(BaseParser):
    def __init__(
        self,
        name: str,
        version: str = "1.0.0",
        *,
        source_type: LogSourceType = LogSourceType.application,
        priority: int = 100,
        enabled: bool = True,
        extensions: tuple[str, ...] = (),
        content_types: tuple[str, ...] = (),
        tags: tuple[str, ...] = (),
        matched: bool = False,
        confidence: float = 0.0,
        reason: str | None = None,
        signals: tuple[str, ...] = (),
        detect_error: str | None = None,
        parse_error: str | None = None,
        parse_result: ParseResult | None = None,
    ) -> None:
        super().__init__()
        self._metadata = ParserMetadata(
            name=name,
            display_name=name.replace("_", " ").title(),
            version=version,
            source_type=source_type,
            supported_extensions=extensions,
            supported_content_types=content_types,
            priority=priority,
            enabled_by_default=enabled,
            tags=tags,
        )
        self._matched = matched
        self._confidence = confidence
        self._reason = reason
        self._signals = signals
        self._detect_error = detect_error
        self._parse_error = parse_error
        self._parse_result = parse_result

    @property
    def metadata(self) -> ParserMetadata:
        return self._metadata

    def detect(
        self,
        raw_log: str,
        context: ParserContext | None = None,
    ) -> DetectionResult:
        if self._detect_error is not None:
            raise RuntimeError(self._detect_error)
        if self._matched:
            return DetectionResult.match(
                self.name,
                self._confidence,
                reason=self._reason,
                signals=self._signals,
            )
        return DetectionResult.no_match(
            self.name,
            confidence=self._confidence,
            reason=self._reason,
            signals=self._signals,
        )

    def parse(
        self,
        raw_log: str,
        context: ParserContext | None = None,
    ) -> ParseResult:
        if self._parse_error is not None:
            raise RuntimeError(self._parse_error)
        if self._parse_result is not None:
            return self._parse_result
        event = LogEvent(
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            source_type=self.source_type,
            message="ok",
            raw_message=raw_log,
            severity=LogSeverity.INFO,
        )
        return ParseResult(status=ParseStatus.success, events=[event])
