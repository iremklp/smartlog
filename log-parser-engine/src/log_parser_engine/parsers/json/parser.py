from __future__ import annotations

from copy import deepcopy
from typing import Any

from log_parser_engine.core import BaseParser, ParserContext
from log_parser_engine.exceptions import (
    JsonDecodingError,
    JsonFieldPathError,
    JsonMappingError,
    JsonParserError,
    JsonProfileError,
    JsonStructureError,
)
from log_parser_engine.models import (
    DetectionResult,
    ErrorType,
    LogSeverity,
    LogSourceType,
    ParseError,
    ParseResult,
    ParseStatus,
    ParserMetadata,
)
from log_parser_engine.models.json_field_mapping import JsonFieldMapping
from log_parser_engine.models.json_log_record import JsonLogRecord
from log_parser_engine.models.json_profile_detection import JsonProfileDetection
from log_parser_engine.normalization import LogNormalizer, NormalizationInput

from .constants import SUPPORTED_PROFILES
from .decoder import decode_json_object, decode_json_value
from .mapping import map_json_record_to_normalization_fields
from .profiles import detect_profile


class JsonLogParser(BaseParser):
    """Parse JSON and JSON Lines log records into canonical LogEvent models."""

    def __init__(
        self,
        normalizer: LogNormalizer | None = None,
        *,
        default_timezone: str = "UTC",
        field_mapping: JsonFieldMapping | None = None,
    ) -> None:
        super().__init__()
        self._normalizer = normalizer or LogNormalizer()
        self._default_timezone = default_timezone
        self._field_mapping = field_mapping or JsonFieldMapping.generic_defaults()

    @property
    def metadata(self) -> ParserMetadata:
        return ParserMetadata(
            name="json_log",
            display_name="JSON and JSON Lines Log Parser",
            version="1.0.0",
            source_type=LogSourceType.JSON,
            description="Parse JSON and JSON Lines log records into canonical events",
            supported_extensions=(".json", ".jsonl", ".ndjson", ".log"),
            supported_content_types=(
                "application/json",
                "application/x-ndjson",
                "application/jsonlines",
                "text/json",
                "text/plain",
            ),
            priority=90,
            enabled_by_default=True,
            supports_multiline=True,
            supports_batch=False,
            thread_safe=True,
            experimental=False,
            tags=("json", "json-lines", "structured", "ecs", "opentelemetry", "serilog"),
        )

    @property
    def normalizer(self) -> LogNormalizer:
        return self._normalizer

    def detect(self, raw_log: str, context: ParserContext | None = None) -> DetectionResult:
        if not isinstance(raw_log, str) or not raw_log.strip():
            return DetectionResult.no_match(self.name, reason="empty input")
        text = raw_log.strip()
        if text.startswith("{") or text.startswith("["):
            try:
                parsed, _ = decode_json_value(text)
            except JsonParserError:
                return DetectionResult.no_match(self.name, reason="not valid JSON")
            if isinstance(parsed, dict):
                return DetectionResult.match(
                    self.name,
                    0.9,
                    reason="JSON object detected",
                    signals=("json_object",),
                )
        if "\n" in text and any(line.strip().startswith("{") for line in text.splitlines() if line.strip()):
            return DetectionResult.match(self.name, 0.8, reason="JSON Lines detected", signals=("json_lines",))
        return DetectionResult.no_match(self.name, reason="JSON structure not detected")

    def parse(self, raw_log: str, context: ParserContext | None = None) -> ParseResult:
        if not isinstance(raw_log, str) or not raw_log.strip():
            return self._failure_result("empty input", ErrorType.EMPTY_INPUT, context=context)

        try:
            data = decode_json_object(raw_log)
        except JsonParserError:
            data = None

        if data is not None:
            record = self._build_record(data, raw_log, context=context)
            return self._parse_record(record, context=context)

        lines = [line for line in raw_log.splitlines() if line.strip()]
        if not lines:
            return self._failure_result("empty input", ErrorType.EMPTY_INPUT, context=context)

        valid_records: list[tuple[str, dict[str, object]]] = []
        for line in lines:
            try:
                parsed = decode_json_object(line)
            except JsonParserError:
                continue
            valid_records.append((line, parsed))

        if not valid_records:
            return self._failure_result("no valid JSON object records found", ErrorType.UNKNOWN_FORMAT, context=context)

        if context is not None and context.strict and len(valid_records) > 1:
            return self._failure_result("multiple JSON records in strict mode", ErrorType.UNKNOWN_FORMAT, context=context)

        selected_line, data = valid_records[0]
        additional_records = len(valid_records) - 1
        record = self._build_record(data, selected_line, context=context, additional_record_count=additional_records)
        return self._parse_record(record, context=context)

    def _parse_single_record(self, raw_json: str, *, context: ParserContext | None) -> ParseResult:
        try:
            data = decode_json_object(raw_json)
        except JsonParserError as exc:
            return self._failure_result(str(exc), ErrorType.UNKNOWN_FORMAT, context=context)
        record = self._build_record(data, raw_json, context=context)
        return self._parse_record(record, context=context)

    def _parse_record(self, record: JsonLogRecord, *, context: ParserContext | None) -> ParseResult:
        try:
            profile = detect_profile(record.data)
            mapped_fields = map_json_record_to_normalization_fields(record.data, profile, self._field_mapping)
            attributes = dict(record.attributes)
            attributes["json_lines"] = {
                "additional_record_count": record.additional_record_count,
                "profile": profile.profile,
            }
            normalization_input = NormalizationInput(
                data=mapped_fields,
                source_type=LogSourceType.JSON,
                attributes={
                    "parser_name": self.name,
                    "parser_version": self.version,
                    "json_profile": profile.profile,
                    "json_profile_confidence": profile.confidence,
                    "json_record": {
                        "line_number": record.line_number,
                        "additional_record_count": record.additional_record_count,
                        "top_level_keys": list(record.top_level_keys),
                    },
                },
            )
            normalized = self._normalizer.normalize(normalization_input, context)
            event = normalized.event
            event = event.model_copy(
                update={
                    "attributes": {
                        **event.attributes,
                        **attributes,
                    },
                    "message": mapped_fields["message"] or event.message,
                    "service": mapped_fields["service"] or event.service,
                    "application": mapped_fields["application"] or event.application,
                    "environment": mapped_fields["environment"] or event.environment,
                    "host": mapped_fields["host"] or event.host,
                    "source": mapped_fields["source"] or event.source,
                    "trace_id": mapped_fields["trace_id"] or event.trace_id,
                    "correlation_id": mapped_fields["correlation_id"] or event.correlation_id,
                    "user_id": mapped_fields["user_id"] or event.user_id,
                    "client_ip": mapped_fields["client_ip"] or event.client_ip,
                    "server_ip": mapped_fields["server_ip"] or event.server_ip,
                    "http_method": mapped_fields["http_method"] or event.http_method,
                    "http_path": mapped_fields["http_path"] or event.http_path,
                    "http_status": mapped_fields["http_status"] or event.http_status,
                    "duration_ms": mapped_fields["duration_ms"] or event.duration_ms,
                    "tags": event.tags,
                    "raw_message": record.raw_json,
                }
            )
            return ParseResult(status=ParseStatus.success, events=[event])
        except JsonFieldPathError as exc:
            return self._failure_result(str(exc), ErrorType.VALIDATION_FAILED, context=context)
        except JsonMappingError as exc:
            return self._failure_result(str(exc), ErrorType.VALIDATION_FAILED, context=context)
        except JsonProfileError as exc:
            return self._failure_result(str(exc), ErrorType.VALIDATION_FAILED, context=context)
        except JsonDecodingError as exc:
            return self._failure_result(str(exc), ErrorType.UNKNOWN_FORMAT, context=context)
        except JsonStructureError as exc:
            return self._failure_result(str(exc), ErrorType.UNKNOWN_FORMAT, context=context)
        except JsonParserError as exc:
            return self._failure_result(str(exc), ErrorType.PARSE_FAILED, context=context)
        except Exception as exc:  # noqa: BLE001
            return self._failure_result(str(exc), ErrorType.INTERNAL_ERROR, context=context)

    def _build_record(
        self,
        data: dict[str, object],
        raw_json: str,
        *,
        context: ParserContext | None,
        additional_record_count: int = 0,
    ) -> JsonLogRecord:
        line_number = None if context is None else context.line_number
        profile = detect_profile(data).profile
        return JsonLogRecord(
            data=data,
            raw_json=raw_json,
            profile=profile,
            line_number=line_number,
            additional_record_count=additional_record_count,
            attributes={"source_name": context.source_name if context else None},
        )

    def _failure_result(
        self,
        message: str,
        error_type: ErrorType,
        *,
        context: ParserContext | None,
    ) -> ParseResult:
        details: dict[str, Any] = {"parser": self.name}
        if context is not None and context.line_number is not None:
            details["line_number"] = str(context.line_number)
        error = ParseError(
            message=message,
            status=ParseStatus.failed,
            error_type=error_type,
            details=details,
        )
        return ParseResult(status=ParseStatus.failed, errors=[error])
