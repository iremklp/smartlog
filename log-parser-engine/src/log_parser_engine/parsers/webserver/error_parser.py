from __future__ import annotations

import re
from typing import Any

from log_parser_engine.core.base_parser import BaseParser, ParserContext
from log_parser_engine.models.detection_result import DetectionResult
from log_parser_engine.models.log_event import LogEvent
from log_parser_engine.models.parse_result import ParseResult
from log_parser_engine.normalization.normalizer import LogNormalizer
from log_parser_engine.models.web_error_record import WebErrorRecord
from .constants import NGINX_ERROR_PREFIXES, SEVERITY_MAP
from .helpers import normalize_severity, normalize_text, normalize_vendor


class ErrorLogParser(BaseParser):
    """Parser for Apache and Nginx error logs."""

    def __init__(self, vendor: str = "generic") -> None:
        self.vendor = normalize_vendor(vendor)
        self.normalizer = LogNormalizer()
        self.metadata = {
            "name": "webserver-error",
            "vendor": self.vendor,
            "format": "error",
            "supports": ["apache", "nginx", "generic"],
        }

    def detect(self, text: str, context: ParserContext | None = None) -> DetectionResult:
        lines = [line for line in text.splitlines() if line.strip()]
        if not lines:
            return DetectionResult(is_match=False, confidence=0.0, reason="empty input")

        sample = lines[0].strip()
        if not any(prefix in sample.lower() for prefix in NGINX_ERROR_PREFIXES):
            return DetectionResult(is_match=False, confidence=0.0, reason="no supported error prefix")

        return DetectionResult(is_match=True, confidence=0.9, reason="looks like a webserver error log")

    def parse(self, text: str, context: ParserContext | None = None) -> ParseResult:
        records: list[LogEvent] = []
        errors: list[dict[str, Any]] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            record = self._parse_line(stripped)
            if record is None:
                errors.append({"line": line, "message": "failed to parse error log line"})
                continue
            normalized = self.normalizer.normalize(log_record=record.model_dump())
            records.append(normalized)
        return ParseResult(events=records, errors=errors, metadata=self.metadata)

    def _parse_line(self, raw_line: str) -> WebErrorRecord | None:
        if not raw_line or raw_line.startswith("not a valid"):
            return None

        match = re.match(r'^(?P<timestamp>\[[^\]]+\])\s+(?P<severity>\w+)\s+(?P<pid>\d+):\s*(?P<message>.+)$', raw_line)
        if not match:
            return None

        severity = normalize_severity(match.group("severity"))
        return WebErrorRecord(
            vendor=self.vendor,
            raw_line=raw_line,
            timestamp=normalize_text(match.group("timestamp")),
            severity=severity,
            pid=normalize_text(match.group("pid")),
            message=normalize_text(match.group("message")),
            attributes={
                "source": "webserver-error",
                "severity_map": SEVERITY_MAP.get(severity.lower(), severity.lower()) if severity else None,
            },
        )
