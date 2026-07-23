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
from log_parser_engine.models.web_access_record import WebAccessRecord
from log_parser_engine.normalization import LogNormalizer, NormalizationInput

from .constants import COMMON_ACCESS_FIELDS, STATUS_CLASS_MAP
from .helpers import normalize_text, normalize_vendor, parse_status


class AccessLogParser(BaseParser):
    """Parser for Apache and Nginx access logs."""

    ACCESS_PATTERN = re.compile(
        r'^(?P<remote_addr>\S+)\s+\S+\s+\S+\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<request>[^"]*)"\s+(?P<status>\d{3})\s+(?P<bytes>\S+)\s+"(?P<referer>[^"]*)"\s+"(?P<agent>[^"]*)"$'
    )

    def __init__(self, vendor: str = "generic", normalizer: LogNormalizer | None = None) -> None:
        super().__init__()
        self.vendor = normalize_vendor(vendor)
        self._normalizer = normalizer or LogNormalizer()
        self._metadata = ParserMetadata(
            name="webserver_access",
            display_name="Webserver Access Log Parser",
            version="1.0.0",
            source_type=self._source_type_for_vendor(self.vendor),
            description="Parse Apache and Nginx access logs",
            supported_extensions=(".log", ".txt"),
            supported_content_types=("text/plain",),
            priority=120,
            enabled_by_default=True,
            supports_multiline=False,
            supports_batch=False,
            thread_safe=True,
            experimental=False,
            tags=("webserver", "apache", "nginx", "access", "http"),
        )

    @property
    def metadata(self) -> ParserMetadata:
        return self._metadata

    def detect(self, raw_log: str, context: ParserContext | None = None) -> DetectionResult:
        if not raw_log or not raw_log.strip():
            return DetectionResult.no_match(self.name, reason="empty input")

        text = raw_log.strip()
        if self.ACCESS_PATTERN.match(text):
            return DetectionResult.match(
                self.name,
                0.9,
                reason="access log structure detected",
                signals=("access_log_pattern",),
            )

        if re.search(r'\s(?:GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\b', text.upper()):
            return DetectionResult.match(self.name, 0.75, reason="request method detected")

        return DetectionResult.no_match(self.name, reason="no supported access log signature")

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
                errors.append(ParseError(message="failed to parse access log line", status=ParseStatus.failed))
                continue
            event = self._normalize_record(record, line, context)
            events.append(event)

        if not events:
            return ParseResult(status=ParseStatus.failed, errors=errors)
        status = ParseStatus.success if not errors else ParseStatus.partial
        return ParseResult(status=status, events=events, errors=errors)

    def _parse_line(self, raw_line: str) -> WebAccessRecord | None:
        match = self.ACCESS_PATTERN.match(raw_line)
        if match is None:
            return None

        request_text = match.group("request")
        request_match = re.match(
            r'^(?P<method>GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+(?P<path>\S+)(?:\s+(?P<version>HTTP/\d\.\d))?$',
            request_text,
        )
        request_path = None
        http_method = None
        http_version = None
        if request_match is not None:
            http_method = request_match.group("method").lower()
            request_path = request_match.group("path")
            http_version = request_match.group("version")

        timestamp_text = match.group("timestamp")
        parsed_timestamp = self._parse_timestamp(timestamp_text)

        return WebAccessRecord(
            vendor=self.vendor,
            raw_line=raw_line,
            remote_addr=normalize_text(match.group("remote_addr")),
            timestamp=normalize_text(timestamp_text),
            request=normalize_text(request_text),
            status_code=parse_status(match.group("status")),
            bytes_sent=parse_status(match.group("bytes")),
            http_referer=normalize_text(match.group("referer")),
            http_user_agent=normalize_text(match.group("agent")),
            request_path=request_path,
            http_method=http_method,
            http_version=http_version,
            attributes={
                "source": "webserver-access",
                "status_class": STATUS_CLASS_MAP.get(str(parse_status(match.group("status")))[0], "unknown") if parse_status(match.group("status")) is not None else "unknown",
                "request_fields": COMMON_ACCESS_FIELDS,
                "timestamp_parsed": parsed_timestamp is not None,
            },
        )

    def _normalize_record(
        self,
        record: WebAccessRecord,
        raw_line: str,
        context: ParserContext | None,
    ) -> Any:
        parsed_timestamp = self._parse_timestamp(record.timestamp) if record.timestamp else None
        normalized_timestamp = parsed_timestamp or datetime.now(timezone.utc)
        status_code = record.status_code
        method = record.http_method or "request"
        path = record.request_path or "/"
        message = f"{method.upper()} {path} -> {status_code}" if status_code is not None else f"{method.upper()} {path}"
        data = {
            "timestamp": normalized_timestamp,
            "severity": LogSeverity.INFO,
            "event_type": "webserver.access",
            "message": message,
            "source": self.vendor,
            "service": self.vendor,
            "host": record.remote_addr,
            "http_method": record.http_method,
            "http_path": record.request_path,
            "http_status": record.status_code,
            "client_ip": record.remote_addr,
            "tags": ["webserver", "access", self.vendor],
        }
        normalization_input = NormalizationInput(
            data=data,
            source_type=self._source_type_for_vendor(self.vendor),
            attributes={
                "parser_name": self.name,
                "parser_version": self.version,
                "vendor": self.vendor,
                "raw_line": raw_line,
                "request": record.request,
                "http_referer": record.http_referer,
                "http_user_agent": record.http_user_agent,
            },
        )
        normalized = self._normalizer.normalize(normalization_input, context)
        event = normalized.event.model_copy(
            update={
                "message": message,
                "raw_message": raw_line,
                "service": self.vendor,
                "source": self.vendor,
                "host": record.remote_addr,
                "client_ip": record.remote_addr,
                "http_method": record.http_method,
                "http_path": record.request_path,
                "http_status": record.status_code,
            }
        )
        return event

    def _parse_timestamp(self, value: str | None) -> datetime | None:
        if not value:
            return None
        for fmt in ("%d/%b/%Y:%H:%M:%S %z", "%d/%b/%Y:%H:%M:%S"):
            try:
                parsed = datetime.strptime(value, fmt)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed.astimezone(timezone.utc)
            except ValueError:
                continue
        return None

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
