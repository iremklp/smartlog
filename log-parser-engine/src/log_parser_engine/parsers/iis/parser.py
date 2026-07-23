from __future__ import annotations

from log_parser_engine.core import BaseParser, ParserContext
from log_parser_engine.exceptions import (
    IisFieldMappingError,
    IisHeaderError,
    IisTokenizationError,
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
from log_parser_engine.models.iis_header import IisW3CHeader
from log_parser_engine.models.iis_record import IisW3CRecord
from log_parser_engine.normalization import LogNormalizer, NormalizationInput

from .header import extract_header_and_data_lines, parse_iis_fields
from .helpers import resolve_fields
from .mapping import map_iis_record_to_normalization_fields
from .tokenizer import build_iis_record


class IisW3CParser(BaseParser):
    """Parse IIS W3C Extended Log Format payloads into canonical LogEvent models."""

    def __init__(self, normalizer: LogNormalizer | None = None) -> None:
        super().__init__()
        self._normalizer = normalizer or LogNormalizer()

    @property
    def metadata(self) -> ParserMetadata:
        return ParserMetadata(
            name="iis_w3c",
            display_name="IIS W3C Extended Log Parser",
            version="1.0.0",
            source_type=LogSourceType.IIS,
            description="Parse IIS W3C Extended Log Format records",
            supported_extensions=(".log",),
            supported_content_types=("text/plain",),
            priority=100,
            enabled_by_default=True,
            supports_multiline=True,
            supports_batch=False,
            thread_safe=True,
            experimental=False,
            tags=("iis", "w3c", "microsoft", "web", "http"),
        )

    @property
    def normalizer(self) -> LogNormalizer:
        return self._normalizer

    def detect(
        self,
        raw_log: str,
        context: ParserContext | None = None,
    ) -> DetectionResult:
        if not raw_log or not raw_log.strip():
            return DetectionResult.no_match(self.name, reason="empty input")

        text = raw_log.strip()
        signals: list[str] = []
        confidence = 0.0

        if "#software:" in text.lower():
            confidence += 0.45
            signals.append("iis_software_directive")
        if "#fields:" in text.lower():
            confidence += 0.30
            signals.append("iis_fields_directive")
        if any(
            marker in text.lower()
            for marker in ("cs-method", "cs-uri-stem", "sc-status", "time-taken")
        ):
            confidence += 0.15
            signals.append("iis_field_markers")
        if self._looks_like_iis_data_line(text):
            confidence += 0.10
            signals.append("iis_data_line")
        if context is not None and context.content_type == "text/plain":
            confidence += 0.02
            signals.append("content_type")
        if context is not None and context.attributes.get("iis_fields"):
            confidence += 0.03
            signals.append("context_fields")

        if confidence >= 0.60 or (
            confidence >= 0.45 and "iis_fields_directive" in signals
        ):
            return DetectionResult.match(
                self.name,
                min(confidence, 1.0),
                reason="IIS W3C header or field structure detected",
                signals=tuple(signals),
            )
        return DetectionResult.no_match(
            self.name,
            confidence=min(confidence, 0.5),
            reason="no IIS W3C signature detected",
        )

    def parse(self, raw_log: str, context: ParserContext | None = None) -> ParseResult:
        if not isinstance(raw_log, str) or not raw_log.strip():
            return self._failure_result(
                "empty input",
                ErrorType.EMPTY_INPUT,
                context=context,
            )

        try:
            header, data_lines = self._extract_header_and_data(raw_log, context)
            if not data_lines:
                return self._failure_result(
                    "no data lines found",
                    ErrorType.UNKNOWN_FORMAT,
                    context=context,
                )

            fields = self._resolve_fields(raw_log, header, context)
            selected_line = data_lines[0]
            selected_line_number = 1
            additional_data_count = len(data_lines) - 1
            strict = True if context is None else context.strict
            record = self._build_record(
                fields=fields,
                line=selected_line,
                line_number=selected_line_number,
                strict=strict,
            )
            mapped = map_iis_record_to_normalization_fields(record)
            normalization_attributes = {
                "parser_name": self.name,
                "iis_header": header.model_dump(),
                **mapped.pop("attributes", {}),
            }
            normalization_input = NormalizationInput(
                data=mapped,
                source_type=LogSourceType.IIS,
                attributes=normalization_attributes,
            )
            normalized = self._normalizer.normalize(normalization_input, context)
            event = normalized.event
            event_attributes = dict(event.attributes)
            event_attributes["iis"] = dict(event_attributes.get("iis", {}))
            event_attributes["iis"]["header_date"] = (
                header.date.isoformat() if header.date else None
            )
            event_attributes["iis"]["additional_data_line_count"] = (
                additional_data_count
            )
            if additional_data_count > 0:
                event_attributes["iis"]["additional_data_lines_present"] = True

            event = event.model_copy(
                update={
                    "attributes": event_attributes,
                    "http_method": mapped.get("http_method"),
                    "http_path": mapped.get("http_path"),
                    "http_status": mapped.get("http_status"),
                    "client_ip": mapped.get("client_ip"),
                    "server_ip": mapped.get("server_ip"),
                    "user_id": mapped.get("user_id"),
                    "duration_ms": mapped.get("duration_ms"),
                    "service": mapped.get("service"),
                    "host": mapped.get("host"),
                    "message": mapped.get("message") or event.message,
                    "raw_message": mapped.get("raw_message") or event.raw_message,
                }
            )
            return ParseResult(status=ParseStatus.success, events=[event])
        except IisHeaderError as exc:
            return self._failure_result(
                str(exc),
                ErrorType.UNKNOWN_FORMAT,
                context=context,
            )
        except IisTokenizationError as exc:
            return self._failure_result(
                str(exc),
                ErrorType.PARSE_FAILED,
                context=context,
            )
        except IisFieldMappingError as exc:
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

    def _resolve_fields(
        self,
        raw_log: str,
        header: IisW3CHeader,
        context: ParserContext | None,
    ) -> tuple[str, ...]:
        try:
            return resolve_fields(raw_log, header, context)
        except ValueError as exc:
            raise IisHeaderError(str(exc)) from exc

    def _extract_header_and_data(
        self,
        raw_log: str,
        context: ParserContext | None,
    ) -> tuple[IisW3CHeader, tuple[str, ...]]:
        try:
            return extract_header_and_data_lines(raw_log)
        except IisHeaderError:
            if context is not None and self._context_has_fields(context):
                fields = self._context_fields(context)
                header = IisW3CHeader(fields=fields, directives={})
                data_lines = tuple(
                    line.strip()
                    for line in raw_log.splitlines()
                    if line.strip() and not line.lstrip().startswith("#")
                )
                return header, data_lines
            raise

    def _build_record(
        self,
        *,
        fields: tuple[str, ...],
        line: str,
        line_number: int | None,
        strict: bool,
    ) -> IisW3CRecord:
        values, missing_fields, extra_values = build_iis_record(
            fields=fields,
            line=line,
            line_number=line_number,
            strict=strict,
        )
        return IisW3CRecord(
            fields=values,
            field_order=fields,
            raw_line=line,
            line_number=line_number,
            extra_values=extra_values,
            missing_fields=missing_fields,
        )

    def _context_has_fields(self, context: ParserContext) -> bool:
        return bool(self._context_fields(context))

    def _context_fields(self, context: ParserContext) -> tuple[str, ...]:
        raw_fields = context.attributes.get("iis_fields")
        if isinstance(raw_fields, str):
            return parse_iis_fields(raw_fields)
        if isinstance(raw_fields, (tuple, list)):
            return parse_iis_fields(" ".join(str(item) for item in raw_fields))
        return tuple()

    def _looks_like_iis_data_line(self, text: str) -> bool:
        lowered = text.lower()
        if "#fields:" in lowered:
            return False
        if any(
            marker in lowered
            for marker in ("http/", "get ", "post ", "put ", "delete ")
        ):
            return True
        return False

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
