from __future__ import annotations

from datetime import datetime
from typing import cast

from log_parser_engine.core import BaseParser, ParserContext
from log_parser_engine.exceptions import (
    RedisClassificationError,
    RedisMappingError,
    RedisParserError,
    RedisTokenizationError,
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

from .classifier import classify_redis_event
from .constants import STRONG_REDIS_MARKERS
from .mapping import map_redis_record_to_normalization_fields
from .tokenizer import parse_redis_log_line


class RedisLogParser(BaseParser):
    """Parse Redis server log lines into canonical LogEvent models."""

    def __init__(
        self,
        normalizer: LogNormalizer | None = None,
        *,
        default_timezone: str = "UTC",
    ) -> None:
        super().__init__()
        self._normalizer = normalizer or LogNormalizer()
        self._default_timezone = default_timezone

    @property
    def metadata(self) -> ParserMetadata:
        return ParserMetadata(
            name="redis_log",
            display_name="Redis Server Log Parser",
            version="1.0.0",
            source_type=LogSourceType.REDIS,
            description="Parse Redis server process log lines",
            supported_extensions=(".log", ".txt"),
            supported_content_types=("text/plain",),
            priority=110,
            enabled_by_default=True,
            supports_multiline=False,
            supports_batch=False,
            thread_safe=True,
            experimental=False,
            tags=(
                "redis",
                "server",
                "sentinel",
                "cluster",
                "replication",
                "persistence",
            ),
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
        lower = text.lower()
        confidence = 0.0
        signals: list[str] = []

        if self._looks_like_redis_pid_prefix(text):
            confidence += 0.35
            signals.append("redis_pid_prefix")
        if self._looks_like_redis_timestamp(text):
            confidence += 0.20
            signals.append("redis_timestamp")
        if self._has_valid_redis_marker(text):
            confidence += 0.10
            signals.append("redis_marker")
        if any(marker in lower for marker in STRONG_REDIS_MARKERS):
            confidence += 0.25
            signals.append("redis_message")
        if self._has_redis_wrapper(text):
            confidence += 0.25
            signals.append("redis_wrapper")
        if (
            context is not None
            and context.source_name is not None
            and "redis" in context.source_name.lower()
        ):
            confidence += 0.10
            signals.append("redis_context")
        if context is not None and context.content_type == "text/plain":
            confidence += 0.02
            signals.append("content_type")

        if confidence >= 0.60:
            return DetectionResult.match(
                self.name,
                min(confidence, 1.0),
                reason="Redis log structure detected",
                signals=tuple(signals),
            )
        return DetectionResult.no_match(
            self.name,
            confidence=min(confidence, 0.5),
            reason="Redis log signature not detected",
        )

    def parse(self, raw_log: str, context: ParserContext | None = None) -> ParseResult:
        if not isinstance(raw_log, str) or not raw_log.strip():
            return self._failure_result(
                "empty input",
                ErrorType.EMPTY_INPUT,
                context=context,
            )

        lines = [line for line in raw_log.splitlines() if line.strip()]
        if not lines:
            return self._failure_result(
                "empty input",
                ErrorType.EMPTY_INPUT,
                context=context,
            )

        if len(lines) > 1 and (context is not None and context.strict):
            return self._failure_result(
                "multiple lines in strict mode",
                ErrorType.UNKNOWN_FORMAT,
                context=context,
            )

        selected_line = lines[0]
        line_number = context.line_number if context is not None else None
        try:
            record = parse_redis_log_line(
                selected_line,
                default_timezone=self._default_timezone,
                reference_datetime=self._reference_datetime(context),
                line_number=line_number,
            )
            classification = classify_redis_event(
                record,
                strict=(context.strict if context is not None else False),
            )
            mapped_fields = map_redis_record_to_normalization_fields(
                record,
                classification,
            )
            normalization_attributes = {
                "parser_name": self.name,
                "parser_version": self.version,
                "redis": {
                    "role": record.role,
                    "role_code": record.role_code,
                    "pid": record.pid,
                    "level_marker": record.level_marker,
                    "timestamp_source": record.timestamp_source,
                    "outer_host": record.outer_host,
                    "outer_process": record.outer_process,
                    "raw_line": record.raw_line,
                },
                "redis_event": dict(classification.attributes),
                "line_number": line_number,
            }
            normalization_input = NormalizationInput(
                data=mapped_fields,
                source_type=LogSourceType.REDIS,
                attributes=normalization_attributes,
            )
            normalized = self._normalizer.normalize(normalization_input, context)
            event = normalized.event
            normalized_attributes = dict(event.attributes)
            redis_attributes = cast(
                dict[str, object],
                normalized_attributes.get("redis", {}),
            )
            redis_payload = cast(
                dict[str, object],
                normalization_attributes["redis"],
            )
            redis_attributes.update(redis_payload)
            normalized_attributes["redis"] = redis_attributes
            normalized_attributes["redis_event"] = cast(
                dict[str, object],
                normalization_attributes["redis_event"],
            )
            event = event.model_copy(
                update={
                    "attributes": normalized_attributes,
                    "timestamp": mapped_fields["timestamp"],
                    "severity": mapped_fields["severity"],
                    "event_type": mapped_fields["event_type"],
                    "message": mapped_fields["message"],
                    "raw_message": selected_line,
                    "service": mapped_fields["service"],
                    "application": mapped_fields["application"],
                    "host": mapped_fields["host"],
                    "source": mapped_fields["source"],
                    "tags": mapped_fields["tags"],
                }
            )
            return ParseResult(status=ParseStatus.success, events=[event])
        except RedisTokenizationError as exc:
            return self._failure_result(
                str(exc),
                ErrorType.UNKNOWN_FORMAT,
                context=context,
            )
        except RedisClassificationError as exc:
            return self._failure_result(
                str(exc),
                ErrorType.VALIDATION_FAILED,
                context=context,
            )
        except RedisMappingError as exc:
            return self._failure_result(
                str(exc),
                ErrorType.VALIDATION_FAILED,
                context=context,
            )
        except RedisParserError as exc:
            return self._failure_result(
                str(exc),
                ErrorType.PARSE_FAILED,
                context=context,
            )
        except Exception as exc:  # noqa: BLE001
            return self._failure_result(
                str(exc),
                ErrorType.INTERNAL_ERROR,
                context=context,
            )

    def _looks_like_redis_pid_prefix(self, text: str) -> bool:
        return bool(__import__("re").match(r"^\d+:([A-Za-z?])\s", text))

    def _looks_like_redis_timestamp(self, text: str) -> bool:
        return bool(
            __import__("re").search(
                r"\b\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b",
                text.lower(),
            )
        )

    def _has_valid_redis_marker(self, text: str) -> bool:
        return any(marker in text for marker in (". ", "- ", "* ", "# "))

    def _has_redis_wrapper(self, text: str) -> bool:
        return (
            "redis-server[" in text
            or "redis-sentinel[" in text
            or "redis-server:" in text
            or "redis-sentinel:" in text
        )

    def _reference_datetime(self, context: ParserContext | None) -> datetime | None:
        if context is None:
            return None
        reference_datetime = context.attributes.get("reference_datetime")
        if isinstance(reference_datetime, datetime):
            return reference_datetime
        return None

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
