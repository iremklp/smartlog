from __future__ import annotations

from datetime import datetime

from log_parser_engine.core import BaseParser, ParserContext
from log_parser_engine.exceptions import (
    NormalizationError,
    SyslogParserError,
    SyslogStructureError,
    SyslogTokenizationError,
)
from log_parser_engine.models import (
    DetectionResult,
    ErrorType,
    LogSourceType,
    ParseError,
    ParseResult,
    ParserMetadata,
    ParseStatus,
)
from log_parser_engine.normalization import LogNormalizer, NormalizationInput

from .mapping import map_syslog_record_to_normalization_fields
from .tokenizer import parse_syslog_message


class Rfc5424SyslogParser(BaseParser):
    """Parse RFC 5424 syslog records into canonical LogEvent models."""

    def __init__(self, normalizer: LogNormalizer | None = None) -> None:
        super().__init__()
        self._normalizer = normalizer or LogNormalizer()

    @property
    def metadata(self) -> ParserMetadata:
        return ParserMetadata(
            name="rfc5424_syslog",
            display_name="RFC 5424 Syslog Parser",
            version="1.0.0",
            source_type=LogSourceType.SYSLOG,
            description="Parse RFC 5424 syslog records",
            supported_extensions=(".log", ".txt"),
            supported_content_types=("text/plain",),
            priority=100,
            enabled_by_default=True,
            supports_multiline=False,
            supports_batch=False,
            thread_safe=True,
            experimental=False,
            tags=("syslog", "rfc5424", "structured-data", "network"),
        )

    @property
    def normalizer(self) -> LogNormalizer:
        return self._normalizer

    def detect(
        self,
        raw_log: str,
        context: ParserContext | None = None,
    ) -> DetectionResult:
        if not isinstance(raw_log, str) or not raw_log.strip():
            return DetectionResult.no_match(self.name, reason="empty input")
        text = raw_log.strip()
        if not text.startswith("<") or ">1 " not in text[:12]:
            return DetectionResult.no_match(self.name, reason="not RFC 5424")
        try:
            parse_syslog_message(
                text,
                line_number=context.line_number if context else None,
            )
        except SyslogTokenizationError:
            return DetectionResult.no_match(
                self.name,
                reason="invalid RFC 5424 header",
            )
        except SyslogStructureError:
            return DetectionResult.no_match(
                self.name,
                reason="invalid RFC 5424 structure",
            )
        return DetectionResult.match(
            self.name,
            0.95,
            reason="RFC 5424 syslog detected",
            signals=("rfc5424",),
        )

    def parse(self, raw_log: str, context: ParserContext | None = None) -> ParseResult:
        if not isinstance(raw_log, str) or not raw_log.strip():
            return self._failure_result(
                "empty input", ErrorType.EMPTY_INPUT, context=context
            )

        try:
            record = parse_syslog_message(
                raw_log,
                default_timezone=self._default_timezone(context),
                reference_datetime=self._reference_datetime(context),
                line_number=context.line_number if context is not None else None,
            )
            if record.version != 1:
                return self._failure_result(
                    "not an RFC 5424 message",
                    ErrorType.UNKNOWN_FORMAT,
                    context=context,
                )
            mapped_fields = map_syslog_record_to_normalization_fields(
                record,
                flavor="rfc5424",
            )
            normalization_input = NormalizationInput(
                data=mapped_fields,
                source_type=LogSourceType.SYSLOG,
                attributes={
                    "parser_name": self.name,
                    "parser_version": self.version,
                    "syslog": {
                        "format": "rfc5424",
                        "priority": record.priority,
                        "facility": record.facility,
                        "severity_code": record.severity_code,
                        "version": record.version,
                        "host": record.host,
                        "application": record.application,
                        "process_id": record.process_id,
                        "message_id": record.message_id,
                        "structured_data": record.structured_data,
                        "raw_header": record.raw_header,
                    },
                },
            )
            normalized = self._normalizer.normalize(normalization_input, context)
            event = normalized.event.with_validated_updates(
                {
                    "attributes": {
                        **normalized.event.attributes,
                        "syslog": {
                            "format": "rfc5424",
                            "priority": record.priority,
                            "facility": record.facility,
                            "severity_code": record.severity_code,
                            "version": record.version,
                            "host": record.host,
                            "application": record.application,
                            "process_id": record.process_id,
                            "message_id": record.message_id,
                            "structured_data": record.structured_data,
                            "raw_header": record.raw_header,
                        },
                    },
                    "message": record.message,
                    "raw_message": record.raw_message,
                    "event_type": mapped_fields["event_type"],
                    "source": mapped_fields["source"],
                    "service": mapped_fields["service"],
                    "application": mapped_fields["application"],
                    "host": mapped_fields["host"],
                    "severity": mapped_fields["severity"],
                    "tags": list(mapped_fields["tags"]),
                }
            )
            return ParseResult(status=ParseStatus.success, events=[event])
        except SyslogParserError as exc:
            return self._failure_result(
                str(exc),
                ErrorType.PARSE_FAILED,
                context=context,
            )
        except NormalizationError as exc:
            return self._failure_result(
                str(exc),
                ErrorType.VALIDATION_FAILED,
                context=context,
            )
        except Exception as exc:  # noqa: BLE001
            return self._failure_result(
                str(exc),
                ErrorType.INTERNAL_ERROR,
                context=context,
            )

    def _default_timezone(self, context: ParserContext | None) -> str:
        if context is None:
            return "UTC"
        value = context.attributes.get("default_timezone")
        if isinstance(value, str) and value.strip():
            return value.strip()
        return "UTC"

    def _reference_datetime(self, context: ParserContext | None) -> datetime | None:
        if context is None:
            return None
        value = context.attributes.get("reference_datetime")
        return value if hasattr(value, "tzinfo") else None

    def _failure_result(
        self,
        message: str,
        error_type: ErrorType,
        *,
        context: ParserContext | None,
    ) -> ParseResult:
        details: dict[str, str] = {"parser": self.name}
        if context is not None and context.line_number is not None:
            details["line_number"] = str(context.line_number)
        error = ParseError(
            message=message,
            status=ParseStatus.failed,
            error_type=error_type,
            details=details,
        )
        return ParseResult(status=ParseStatus.failed, errors=[error])
