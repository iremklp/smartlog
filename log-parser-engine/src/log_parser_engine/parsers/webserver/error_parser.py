from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from log_parser_engine.core import BaseParser, ParserContext
from log_parser_engine.models import (
    DetectionResult,
    LogSeverity,
    LogSourceType,
    ParseError,
    ParseResult,
    ParseStatus,
    ParserMetadata,
)
from log_parser_engine.models.web_error_record import WebErrorRecord
from log_parser_engine.normalization import LogNormalizer, NormalizationInput

from .constants import NGINX_ERROR_PREFIXES, SEVERITY_MAP
from .helpers import normalize_severity, normalize_text, normalize_vendor


class ErrorLogParser(BaseParser):
    """Parser for Apache and Nginx error logs."""

    def __init__(self, vendor: str = "generic", normalizer: LogNormalizer | None = None) -> None:
        super().__init__()
        self.vendor = normalize_vendor(vendor)
        self._normalizer = normalizer or LogNormalizer()
        self._metadata = ParserMetadata(
            name="webserver_error",
            display_name="Webserver Error Log Parser",
            version="1.0.0",
            source_type=self._source_type_for_vendor(self.vendor),
            description="Parse Apache and Nginx error logs",
            supported_extensions=(".log", ".txt"),
            supported_content_types=("text/plain",),
            priority=121,
            enabled_by_default=True,
            supports_multiline=False,
            supports_batch=False,
            thread_safe=True,
            experimental=False,
            tags=("webserver", "apache", "nginx", "error", "http"),
        )

    @property
    def metadata(self) -> ParserMetadata:
        return self._metadata

    def detect(self, raw_log: str, context: ParserContext | None = None) -> DetectionResult:
        if not raw_log or not raw_log.strip():
            return DetectionResult.no_match(self.name, reason="empty input")

        sample = raw_log.strip()
        if re.search(r'\[(?:error|warn|crit|notice)\]', sample.lower()):
            return DetectionResult.match(self.name, 0.9, reason="error log prefix detected")

        if any(prefix in sample.lower() for prefix in NGINX_ERROR_PREFIXES):
            return DetectionResult.match(self.name, 0.8, reason="error marker detected")

        return DetectionResult.no_match(self.name, reason="no supported error log signature")

    def parse(self, raw_log: str, context: ParserContext | None = None) -> ParseResult:
        if not isinstance(raw_log, str) or not raw_log.strip():
            return self._failure_result("empty input", context)

        lines = [line.strip() for line in raw_log.splitlines() if line.strip()]
        if not lines:
            return self._failure_result("empty input", context)

        events: list[Any] = []
        errors: list[ParseError] = []
        for line in lines:
            record = self._parse_line(line)
            if record is None:
                errors.append(ParseError(message="failed to parse error log line", status=ParseStatus.failed))
                continue
            event = self._normalize_record(record, line, context)
            events.append(event)

        if not events:
            return ParseResult(status=ParseStatus.failed, errors=errors)
        status = ParseStatus.success if not errors else ParseStatus.partial
        return ParseResult(status=status, events=events, errors=errors)

    def _parse_line(self, raw_line: str) -> WebErrorRecord | None:
        if not raw_line or raw_line.startswith("not a valid"):
            return None

        match = re.match(
            r'^(?P<timestamp>\[[^\]]+\])\s+(?P<severity>\[[^\]]+\]|\w+)\s*(?:\[(?P<subsystem>[^\]]+)\]\s*)?(?P<message>.+)$',
            raw_line,
        )
        if not match:
            return None

        severity_token = match.group("severity")
        severity_text = severity_token.strip("[]") if severity_token else None
        severity = normalize_severity(severity_text)
        return WebErrorRecord(
            vendor=self.vendor,
            raw_line=raw_line,
            timestamp=normalize_text(match.group("timestamp")),
            severity=severity,
            pid=None,
            message=normalize_text(match.group("message")),
            attributes={
                "source": "webserver-error",
                "severity_map": SEVERITY_MAP.get(severity.lower(), severity.lower()) if severity else None,
            },
        )

    def _normalize_record(
        self,
        record: WebErrorRecord,
        raw_line: str,
        context: ParserContext | None,
    ) -> Any:
        parsed_timestamp = self._parse_timestamp(record.timestamp) if record.timestamp else None
        timestamp = parsed_timestamp or datetime.now(timezone.utc)
        severity = self._severity_to_log_severity(record.severity)
        data = {
            "timestamp": timestamp,
            "severity": severity,
            "event_type": "webserver.error",
            "message": record.message or raw_line,
            "source": self.vendor,
            "service": self.vendor,
            "host": None,
            "tags": ["webserver", "error", self.vendor],
        }
        normalization_input = NormalizationInput(
            data=data,
            source_type=self._source_type_for_vendor(self.vendor),
            attributes={
                "parser_name": self.name,
                "parser_version": self.version,
                "vendor": self.vendor,
                "raw_line": raw_line,
                "severity": record.severity,
            },
        )
        normalized = self._normalizer.normalize(normalization_input, context)
        event = normalized.event.model_copy(
            update={
                "message": record.message or raw_line,
                "raw_message": raw_line,
                "service": self.vendor,
                "source": self.vendor,
                "severity": severity,
            }
        )
        return event

    def _parse_timestamp(self, value: str | None) -> datetime | None:
        if not value:
            return None
        cleaned = value.strip("[]")
        for fmt in ("%a %b %d %H:%M:%S %Y", "%d/%b/%Y:%H:%M:%S"):
            try:
                parsed = datetime.strptime(cleaned, fmt)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed.astimezone(timezone.utc)
            except ValueError:
                continue
        return None

    def _severity_to_log_severity(self, value: str | None) -> LogSeverity:
        if value is None:
            return LogSeverity.WARNING
        normalized = value.strip().lower()
        if normalized in {"error", "crit", "critical"}:
            return LogSeverity.ERROR
        if normalized in {"warn", "warning"}:
            return LogSeverity.WARNING
        if normalized in {"notice"}:
            return LogSeverity.NOTICE
        if normalized in {"info"}:
            return LogSeverity.INFO
        return LogSeverity.WARNING

    def _failure_result(self, message: str, context: ParserContext | None) -> ParseResult:
        details = {"parser": self.name}
        if context is not None and context.line_number is not None:
            details["line_number"] = str(context.line_number)
        error = ParseError(message=message, status=ParseStatus.failed, details=details)
        return ParseResult(status=ParseStatus.failed, errors=[error])

    def _source_type_for_vendor(self, vendor: str) -> LogSourceType:
        if vendor == "nginx":
            return LogSourceType.NGINX
        if vendor == "apache":
            return LogSourceType.APACHE
        return LogSourceType.APPLICATION
