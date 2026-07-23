from __future__ import annotations

import re
from typing import Any

from log_parser_engine.core.base_parser import BaseParser, ParserContext
from log_parser_engine.models.detection_result import DetectionResult
from log_parser_engine.models.log_event import LogEvent
from log_parser_engine.models.parse_result import ParseResult
from log_parser_engine.normalization.normalizer import LogNormalizer
from log_parser_engine.models.web_access_record import WebAccessRecord
from .constants import COMBINED_ACCESS_FIELDS, COMMON_ACCESS_FIELDS, HTTP_METHODS, STATUS_CLASS_MAP
from .helpers import detect_http_method, normalize_text, normalize_vendor, parse_status


class AccessLogParser(BaseParser):
    """Parser for Apache and Nginx access logs."""

    def __init__(self, vendor: str = "generic") -> None:
        self.vendor = normalize_vendor(vendor)
        self.normalizer = LogNormalizer()
        self.metadata = {
            "name": "webserver-access",
            "vendor": self.vendor,
            "format": "access",
            "supports": ["apache", "nginx", "generic"],
        }

    def detect(self, text: str, context: ParserContext | None = None) -> DetectionResult:
        lines = [line for line in text.splitlines() if line.strip()]
        if not lines:
            return DetectionResult(is_match=False, confidence=0.0, reason="empty input")

        sample = lines[0].strip()
        if not re.search(r'\s(?:GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\b', sample.upper()):
            return DetectionResult(is_match=False, confidence=0.0, reason="no supported request method")

        return DetectionResult(is_match=True, confidence=0.9, reason="looks like a webserver access log")

    def parse(self, text: str, context: ParserContext | None = None) -> ParseResult:
        records: list[LogEvent] = []
        errors: list[dict[str, Any]] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            record = self._parse_line(stripped)
            if record is None:
                errors.append({"line": line, "message": "failed to parse access log line"})
                continue
            normalized = self.normalizer.normalize(log_record=record.model_dump())
            records.append(normalized)
        return ParseResult(events=records, errors=errors, metadata=self.metadata)

    def _parse_line(self, raw_line: str) -> WebAccessRecord | None:
        parts = raw_line.split(' ')
        if len(parts) < 6:
            return None

        remote_addr = parts[0]
        remote_user = parts[2] if len(parts) > 2 else None
        timestamp = parts[3] if len(parts) > 3 else None
        request = parts[4] if len(parts) > 4 else None

        if request is None or request.startswith('"'):
            return None

        request_path = None
        http_method = None
        http_version = None
        if request:
            request_match = re.match(r'^(?P<method>GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+(?P<path>\S+)(?:\s+(?P<version>HTTP/\d\.\d))?', request.upper())
            if request_match:
                http_method = request_match.group('method').lower()
                request_path = request_match.group('path')
                http_version = request_match.group('version')

        status_code = None
        bytes_sent = None
        if len(parts) > 5:
            status_code = parse_status(parts[-2]) if len(parts) >= 6 else None
            bytes_sent = parse_status(parts[-1])

        # Try to recover a more realistic request line from the line if available.
        request_text = None
        if len(parts) > 4 and parts[4] != '-':
            request_text = ' '.join(parts[4:len(parts)-2]) if len(parts) > 6 else None

        record = WebAccessRecord(
            vendor=self.vendor,
            raw_line=raw_line,
            remote_addr=normalize_text(remote_addr),
            remote_user=normalize_text(remote_user),
            timestamp=normalize_text(timestamp),
            request=normalize_text(request_text or request),
            status_code=status_code,
            bytes_sent=bytes_sent,
            request_path=request_path,
            http_method=http_method,
            http_version=http_version,
            attributes={
                "source": "webserver-access",
                "status_class": STATUS_CLASS_MAP.get(str(status_code)[0], "unknown") if status_code is not None else "unknown",
                "request_fields": COMMON_ACCESS_FIELDS,
            },
        )
        return record
