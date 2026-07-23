from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from log_parser_engine.models import (
    DetectionResult,
    ErrorType,
    LogSourceType,
    ParseError,
    ParseResult,
    ParseStatus,
)
from log_parser_engine.models.parser_metadata import ParserMetadata

from .parser_context import ParserContext


class BaseParser(ABC):
    """Abstract contract for all future log parsers."""

    MAX_ERROR_RAW_LENGTH = 500

    def __init__(self) -> None:
        self._metadata: ParserMetadata | None = None

    @property
    @abstractmethod
    def metadata(self) -> ParserMetadata:
        """Return immutable parser metadata for this parser implementation."""

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def version(self) -> str:
        return self.metadata.version

    @property
    def source_type(self) -> LogSourceType:
        return self.metadata.source_type

    def is_enabled(self) -> bool:
        return self.metadata.enabled_by_default

    def safe_detect(
        self,
        raw_log: str,
        context: ParserContext | None = None,
    ) -> DetectionResult:
        """Return a safe detection result even when the underlying parser fails."""
        if not isinstance(raw_log, str):
            return DetectionResult.no_match(
                self.name,
                reason="input must be a string",
            )
        if not raw_log.strip():
            return DetectionResult.no_match(self.name, reason="empty input")

        try:
            result = self.detect(raw_log, context)
        except Exception as exc:  # noqa: BLE001
            return DetectionResult.no_match(
                self.name,
                reason=f"detect failed: {type(exc).__name__}",
                metadata={"error": str(exc)},
            )

        if not isinstance(result, DetectionResult):
            return DetectionResult.no_match(
                self.name,
                reason="detect returned an invalid result",
            )
        return result

    def safe_parse(
        self,
        raw_log: str,
        context: ParserContext | None = None,
    ) -> ParseResult:
        """Return a safe parse result even when the underlying parser fails."""
        if not isinstance(raw_log, str):
            error = ParseError(
                message="input must be a string",
                status=ParseStatus.failed,
                error_type=ErrorType.EMPTY_INPUT,
            )
            return ParseResult(status=ParseStatus.failed, errors=[error])

        if not raw_log.strip():
            error = ParseError(
                message="empty input",
                status=ParseStatus.failed,
                error_type=ErrorType.EMPTY_INPUT,
            )
            return ParseResult(status=ParseStatus.failed, errors=[error])

        try:
            result = self.parse(raw_log, context)
        except Exception as exc:  # noqa: BLE001
            error = self._build_error_from_exception(exc, context)
            return ParseResult(status=ParseStatus.failed, errors=[error])

        if not isinstance(result, ParseResult):
            error = ParseError(
                message="parse returned an invalid result",
                status=ParseStatus.failed,
                error_type=ErrorType.INTERNAL_ERROR,
            )
            return ParseResult(status=ParseStatus.failed, errors=[error])

        return result

    @abstractmethod
    def detect(
        self,
        raw_log: str,
        context: ParserContext | None = None,
    ) -> DetectionResult:
        """Return a detection result indicating how strongly the parser
        matches a log."""

    @abstractmethod
    def parse(
        self,
        raw_log: str,
        context: ParserContext | None = None,
    ) -> ParseResult:
        """Parse a log into a normalized LogEvent result."""

    def _truncate_raw(self, raw_log: str) -> str:
        if len(raw_log) <= self.MAX_ERROR_RAW_LENGTH:
            return raw_log
        return raw_log[: self.MAX_ERROR_RAW_LENGTH - 3] + "..."

    def _build_error_from_exception(
        self,
        exc: Exception,
        context: ParserContext | None,
    ) -> ParseError:
        line_number = None
        if context is not None:
            line_number = context.line_number
        details: dict[str, Any] = {"parser": self.name}
        if line_number is not None:
            details["line_number"] = str(line_number)
        details["exception_type"] = type(exc).__name__
        return ParseError(
            message=f"{self.name} failed: {exc.__class__.__name__}",
            status=ParseStatus.failed,
            error_type=ErrorType.INTERNAL_ERROR,
            details=details,
        )
