from __future__ import annotations

import re
from datetime import datetime, timezone

from log_parser_engine.core import BaseParser, ParserContext
from log_parser_engine.models import (
    DetectionResult,
    LogEvent,
    LogSeverity,
    LogSourceType,
    ParseError,
    ParseResult,
    ParserMetadata,
    ParseStatus,
    WebErrorRecord,
)
from log_parser_engine.normalization import LogNormalizer, NormalizationInput

from .constants import SEVERITY_MAP
from .helpers import normalize_severity, normalize_text, normalize_vendor


class ApacheNginxErrorLogParser(BaseParser):
    """Parser for Apache and Nginx error logs."""

    APACHE_PATTERN = re.compile(
        r'^\[(?P<timestamp>[^\]]+)\]\s+\[(?P<severity>[^\]]+)\]\s+(?:(?P<context>\[[^\]]+\])\s+)?(?P<message>.+)$'
    )
    NGINX_PATTERN = re.compile(
        r'^(?P<timestamp>\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})\s+'
        r'\[(?P<severity>[^\]]+)\]\s+'
        r'(?P<pid>\d+#\d+):\s+(?P<connection>\*\d+)\s+(?P<message>.+)$'
    )

    def __init__(
        self,
        vendor: str = "generic",
        normalizer: LogNormalizer | None = None,
    ) -> None:
        super().__init__()
        self.vendor = normalize_vendor(vendor)
        self._normalizer = normalizer or LogNormalizer()
        self._metadata = ParserMetadata(
            name="apache_nginx_error",
            display_name="Apache Nginx Error Log Parser",
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
        if self._metadata is None:
            raise RuntimeError("metadata has not been initialized")
        return self._metadata

    def detect(
        self,
        raw_log: str,
        context: ParserContext | None = None,
    ) -> DetectionResult:
        if not raw_log or not raw_log.strip():
            return DetectionResult.no_match(self.name, reason="empty input")

        sample = raw_log.strip()
        if self.APACHE_PATTERN.match(sample) or self.NGINX_PATTERN.match(sample):
            return DetectionResult.match(
                self.name,
                0.9,
                reason="error log structure detected",
            )

        if re.search(r"\[(?:error|warn|crit|notice)\]", sample.lower()):
            return DetectionResult.match(
                self.name,
                0.75,
                reason="error log prefix detected",
            )

        return DetectionResult.no_match(
            self.name,
            reason="no supported error log signature",
        )

    def parse(self, raw_log: str, context: ParserContext | None = None) -> ParseResult:
        if not isinstance(raw_log, str) or not raw_log.strip():
            return self._failure_result("empty input", context)

        lines = [line.strip() for line in raw_log.splitlines() if line.strip()]
        if not lines:
            return self._failure_result("empty input", context)

        events: list[LogEvent] = []
        errors: list[ParseError] = []
        for line in lines:
            record = self._parse_line(line)
            if record is None:
                errors.append(
                    ParseError(
                        message="failed to parse error log line",
                        status=ParseStatus.failed,
                    )
                )
                continue
            events.append(self._normalize_record(record, line, context))

        if not events:
            return ParseResult(status=ParseStatus.failed, errors=errors)
        status = ParseStatus.success if not errors else ParseStatus.partial
        return ParseResult(status=status, events=events, errors=errors)

    def _parse_line(self, raw_line: str) -> WebErrorRecord | None:
        if not raw_line or raw_line.startswith("not a valid"):
            return None

        nginx_match = self.NGINX_PATTERN.match(raw_line)
        if nginx_match is not None:
            return self._parse_nginx_line(raw_line, nginx_match)

        apache_match = self.APACHE_PATTERN.match(raw_line)
        if apache_match is not None:
            return self._parse_apache_line(raw_line, apache_match)

        return None

    def _parse_apache_line(self, raw_line: str, match: re.Match[str]) -> WebErrorRecord:
        severity = normalize_severity(match.group("severity"))
        context = normalize_text(match.group("context"))
        message = normalize_text(match.group("message"))
        client = None
        if context is not None:
            client_match = re.match(r'^\[client (?P<client>[^\]]+)\]$', context)
            if client_match is not None:
                client = client_match.group("client")

        return WebErrorRecord(
            vendor=self.vendor,
            raw_line=raw_line,
            timestamp=normalize_text(match.group("timestamp")),
            severity=severity,
            pid=None,
            connection_id=None,
            message=message,
            client=client,
            attributes={
                "source": "webserver-error",
                "severity_map": (
                    SEVERITY_MAP.get(severity.lower(), severity.lower())
                    if severity
                    else None
                ),
            },
        )

    def _parse_nginx_line(self, raw_line: str, match: re.Match[str]) -> WebErrorRecord:
        severity = normalize_severity(match.group("severity"))
        core_message, attributes = self._split_nginx_message(match.group("message"))

        return WebErrorRecord(
            vendor=self.vendor,
            raw_line=raw_line,
            timestamp=normalize_text(match.group("timestamp")),
            severity=severity,
            pid=normalize_text(match.group("pid")),
            connection_id=normalize_text(match.group("connection")),
            message=normalize_text(core_message),
            client=attributes.get("client"),
            server=attributes.get("server"),
            request=attributes.get("request"),
            host=attributes.get("host"),
            upstream=attributes.get("upstream"),
            attributes={
                "source": "webserver-error",
                "nginx": attributes,
                "severity_map": (
                    SEVERITY_MAP.get(severity.lower(), severity.lower())
                    if severity
                    else None
                ),
            },
        )

    def _split_nginx_message(self, message: str) -> tuple[str, dict[str, str]]:
        parts = re.split(r", (?=[a-z_]+: )", message)
        if not parts:
            return message, {}

        core_message = parts[0].strip()
        attributes: dict[str, str] = {}
        for segment in parts[1:]:
            key, sep, value = segment.partition(": ")
            if not sep:
                continue
            cleaned_key = key.strip().lower()
            cleaned_value = value.strip().strip('"')
            if cleaned_key:
                attributes[cleaned_key] = cleaned_value
        return core_message, attributes

    def _normalize_record(
        self,
        record: WebErrorRecord,
        raw_line: str,
        context: ParserContext | None,
    ) -> LogEvent:
        parsed_timestamp = (
            self._parse_timestamp(record.timestamp)
            if record.timestamp
            else None
        )
        timestamp = parsed_timestamp or datetime.now(timezone.utc)
        severity = self._severity_to_log_severity(record.severity)
        data = {
            "timestamp": timestamp,
            "severity": severity,
            "event_type": "webserver.error",
            "message": record.message or raw_line,
            "source": self.vendor,
            "service": self.vendor,
            "host": record.host,
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
                "client": record.client,
                "server": record.server,
                "request": record.request,
                "upstream": record.upstream,
            },
        )
        normalized = self._normalizer.normalize(normalization_input, context)
        return normalized.event.with_validated_updates(
            {
                "message": record.message or raw_line,
                "raw_message": raw_line,
                "service": self.vendor,
                "source": self.vendor,
                "severity": severity,
            }
        )

    def _parse_timestamp(self, value: str | None) -> datetime | None:
        if not value:
            return None
        cleaned = value.strip("[]")
        for fmt in ("%a %b %d %H:%M:%S %Y", "%Y/%m/%d %H:%M:%S", "%d/%b/%Y:%H:%M:%S"):
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

    def _failure_result(
        self,
        message: str,
        context: ParserContext | None,
    ) -> ParseResult:
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
