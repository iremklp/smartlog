from __future__ import annotations

from typing import Any

from log_parser_engine.core import BaseParser, ParserContext
from log_parser_engine.exceptions import (
    NormalizationError,
    WindowsEventMappingError,
    WindowsEventParserError,
    WindowsEventStructureError,
    WindowsEventXmlError,
)
from log_parser_engine.models import (
    DetectionResult,
    ErrorType,
    LogSourceType,
    ParseError,
    ParseResult,
    ParserMetadata,
    ParseStatus,
    WindowsEventRecord,
)
from log_parser_engine.normalization import LogNormalizer, NormalizationInput

from .decoder import (
    decode_windows_event_xml,
    extract_element_text,
    parse_windows_timestamp,
)
from .mapping import map_windows_event_record_to_normalization_fields


class WindowsEventXmlParser(BaseParser):
    """Parse Windows Event XML payloads into canonical LogEvent models."""

    def __init__(self, normalizer: LogNormalizer | None = None) -> None:
        super().__init__()
        self._normalizer = normalizer or LogNormalizer()

    @property
    def metadata(self) -> ParserMetadata:
        return ParserMetadata(
            name="windows_event_xml",
            display_name="Windows Event XML Parser",
            version="1.0.0",
            source_type=LogSourceType.WINDOWS_EVENT,
            description="Parse Windows Event XML exports into canonical events",
            supported_extensions=(".xml", ".evtx.xml", ".log"),
            supported_content_types=("application/xml", "text/xml", "text/plain"),
            priority=95,
            enabled_by_default=True,
            supports_multiline=True,
            supports_batch=False,
            thread_safe=True,
            experimental=False,
            tags=("windows", "event-log", "xml", "security", "system"),
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
        text = raw_log.lstrip()
        if not text.startswith("<") or "<Event" not in text:
            return DetectionResult.no_match(self.name, reason="not Windows Event XML")
        try:
            root = decode_windows_event_xml(raw_log)
        except WindowsEventXmlError:
            return DetectionResult.no_match(
                self.name,
                reason="invalid Windows Event XML",
            )
        except WindowsEventStructureError:
            return DetectionResult.no_match(
                self.name,
                reason="unsupported Windows Event XML",
            )

        signals: list[str] = ["windows_event_xml"]
        confidence = 0.8
        if root.find(".//{*}System") is not None:
            confidence += 0.1
            signals.append("system_block")
        if root.find(".//{*}EventData") is not None:
            confidence += 0.1
            signals.append("event_data")
        return DetectionResult.match(
            self.name,
            min(confidence, 1.0),
            reason="Windows Event XML detected",
            signals=tuple(signals),
        )

    def parse(self, raw_log: str, context: ParserContext | None = None) -> ParseResult:
        if not isinstance(raw_log, str) or not raw_log.strip():
            return self._failure_result(
                "empty input", ErrorType.EMPTY_INPUT, context=context
            )

        try:
            root = decode_windows_event_xml(raw_log)
            record = self._build_record(root, raw_log, context=context)
            mapped_fields = map_windows_event_record_to_normalization_fields(record)
            normalization_input = NormalizationInput(
                data=mapped_fields,
                source_type=LogSourceType.WINDOWS_EVENT,
                attributes={
                    "parser_name": self.name,
                    "parser_version": self.version,
                    "windows_event": {
                        "event_id": record.event_id,
                        "provider_name": record.provider_name,
                        "channel": record.channel,
                        "computer": record.computer,
                        "level": record.level,
                        "task": record.task,
                        "opcode": record.opcode,
                        "keywords": record.keywords,
                        "record_id": record.record_id,
                        "execution_process_id": record.execution_process_id,
                        "execution_thread_id": record.execution_thread_id,
                        "version": record.version,
                        "event_data": dict(record.event_data),
                    },
                },
            )
            normalized = self._normalizer.normalize(normalization_input, context)
            event = normalized.event.with_validated_updates(
                {
                    "attributes": {
                        **normalized.event.attributes,
                        "windows_event": {
                            "event_id": record.event_id,
                            "provider_name": record.provider_name,
                            "channel": record.channel,
                            "computer": record.computer,
                            "level": record.level,
                            "task": record.task,
                            "opcode": record.opcode,
                            "keywords": record.keywords,
                            "record_id": record.record_id,
                            "execution_process_id": record.execution_process_id,
                            "execution_thread_id": record.execution_thread_id,
                            "version": record.version,
                            "event_data": dict(record.event_data),
                            "raw_xml": record.raw_xml,
                        },
                    },
                    "message": record.message,
                    "raw_message": record.raw_xml,
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
        except WindowsEventXmlError as exc:
            return self._failure_result(
                str(exc), ErrorType.UNKNOWN_FORMAT, context=context
            )
        except WindowsEventStructureError as exc:
            return self._failure_result(
                str(exc), ErrorType.UNKNOWN_FORMAT, context=context
            )
        except WindowsEventMappingError as exc:
            return self._failure_result(
                str(exc), ErrorType.VALIDATION_FAILED, context=context
            )
        except NormalizationError as exc:
            return self._failure_result(
                str(exc), ErrorType.VALIDATION_FAILED, context=context
            )
        except WindowsEventParserError as exc:
            return self._failure_result(
                str(exc), ErrorType.PARSE_FAILED, context=context
            )
        except Exception as exc:  # noqa: BLE001
            return self._failure_result(
                str(exc), ErrorType.INTERNAL_ERROR, context=context
            )

    def _build_record(
        self,
        root: Any,
        raw_xml: str,
        *,
        context: ParserContext | None,
    ) -> WindowsEventRecord:
        system = root.find(".//{*}System")
        if system is None:
            raise WindowsEventStructureError("missing System block")

        event_id_text = extract_element_text(system.find(".//{*}EventID"))
        if event_id_text is None:
            raise WindowsEventStructureError("missing EventID")
        timestamp_element = system.find(".//{*}TimeCreated")
        timestamp_value = (
            None
            if timestamp_element is None
            else timestamp_element.attrib.get("SystemTime")
        )
        if timestamp_value is None:
            raise WindowsEventStructureError("missing TimeCreated SystemTime")

        event_data: dict[str, str] = {}
        data_block = root.find(".//{*}EventData")
        if data_block is not None:
            for index, item in enumerate(list(data_block)):
                key = item.attrib.get("Name") or f"Data{index}"
                value = extract_element_text(item)
                if value is not None:
                    event_data[key] = value

        provider = system.find(".//{*}Provider")
        execution = system.find(".//{*}Execution")
        correlation = system.find(".//{*}Correlation")
        rendering = root.find(".//{*}RenderingInfo/{*}Message")
        if rendering is None:
            rendering = root.find(".//{*}Message")

        message = extract_element_text(rendering)
        if message is None:
            message = _build_event_message(event_id_text, event_data)

        level_text = extract_element_text(system.find(".//{*}Level"))
        task_text = extract_element_text(system.find(".//{*}Task"))
        opcode_text = extract_element_text(system.find(".//{*}Opcode"))
        keywords_text = extract_element_text(system.find(".//{*}Keywords"))
        record_id_text = extract_element_text(system.find(".//{*}EventRecordID"))

        return WindowsEventRecord(
            event_id=int(event_id_text),
            timestamp=parse_windows_timestamp(timestamp_value),
            provider_name=provider.attrib.get("Name") if provider is not None else None,
            channel=extract_element_text(system.find(".//{*}Channel")),
            computer=extract_element_text(system.find(".//{*}Computer")),
            level=int(level_text)
            if level_text is not None and level_text.isdigit()
            else None,
            task=int(task_text)
            if task_text is not None and task_text.isdigit()
            else None,
            opcode=int(opcode_text)
            if opcode_text is not None and opcode_text.isdigit()
            else None,
            keywords=keywords_text,
            record_id=int(record_id_text)
            if record_id_text is not None and record_id_text.isdigit()
            else None,
            execution_process_id=_safe_int(
                execution.attrib.get("ProcessID") if execution is not None else None
            ),
            execution_thread_id=_safe_int(
                execution.attrib.get("ThreadID") if execution is not None else None
            ),
            version=_safe_int(system.findtext(".//{*}Version")),
            message=message,
            raw_xml=raw_xml,
            line_number=context.line_number if context is not None else None,
            event_data=event_data,
            attributes={
                "source_name": context.source_name if context is not None else None,
                "correlation_activity_id": correlation.attrib.get("ActivityID")
                if correlation is not None
                else None,
            },
        )

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


def _build_event_message(event_id: str, event_data: dict[str, str]) -> str:
    if event_data:
        summary = ", ".join(
            f"{key}={value}" for key, value in sorted(event_data.items())
        )
        return f"Windows Event {event_id}: {summary}"
    return f"Windows Event {event_id}"


def _safe_int(value: str | None) -> int | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if cleaned.isdigit():
        return int(cleaned)
    return None
