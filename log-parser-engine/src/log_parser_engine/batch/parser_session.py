from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Literal, Protocol, cast

from log_parser_engine.core import ParserContext, ParserManager
from log_parser_engine.models import (
    BatchItem,
    BatchItemResult,
    ParserSessionInfo,
)

from .helpers import extract_error_code, extract_error_message, parse_result_succeeded
from .options import BatchParseOptions
from .record_reader import SourceRecord
from .state import ParserRecordStrategy


class ParserStateAdapter(Protocol):
    parser_name: str

    def classify_item(self, item: SourceRecord) -> str: ...

    def process_non_data_item(
        self, item: SourceRecord, state: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]: ...

    def build_context_attributes(self, state: dict[str, Any]) -> dict[str, Any]: ...


class StatelessLineAdapter:
    def __init__(self, parser_name: str) -> None:
        self.parser_name = parser_name

    def classify_item(self, item: SourceRecord) -> str:
        if item.kind_hint == "blank":
            return "blank"
        return "data"

    def process_non_data_item(
        self, item: SourceRecord, state: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        return "skipped", {}

    def build_context_attributes(self, state: dict[str, Any]) -> dict[str, Any]:
        return {}


class IisW3CStateAdapter(StatelessLineAdapter):
    def classify_item(self, item: SourceRecord) -> str:
        if item.raw is None:
            return "data"
        stripped = item.raw.strip()
        if stripped == "":
            return "blank"
        if stripped.startswith("#"):
            if (
                stripped.lower().startswith("#fields:")
                or stripped.lower().startswith("#software:")
                or stripped.lower().startswith("#version:")
                or stripped.lower().startswith("#date:")
            ):
                return "header"
            return "comment"
        return "data"

    def process_non_data_item(
        self, item: SourceRecord, state: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        if item.raw is None:
            return "skipped", {}
        stripped = item.raw.strip()
        lowered = stripped.lower()
        updates: dict[str, Any] = {}
        header = dict(state.get("iis_header", {}))
        if lowered.startswith("#fields:"):
            value = stripped.split(":", 1)[1].strip() if ":" in stripped else ""
            fields = tuple(
                part.strip().lower() for part in value.split() if part.strip()
            )
            state["iis_fields"] = fields
            updates["iis_fields"] = fields
            header["fields"] = fields
            state["iis_header"] = header
            updates["iis_header"] = dict(header)
            return "header", updates
        if lowered.startswith("#software:"):
            value = stripped.split(":", 1)[1].strip() if ":" in stripped else ""
            header["software"] = value
            state["iis_header"] = header
            updates["iis_header"] = dict(header)
            return "header", updates
        if lowered.startswith("#version:"):
            value = stripped.split(":", 1)[1].strip() if ":" in stripped else ""
            header["version"] = value
            state["iis_header"] = header
            updates["iis_header"] = dict(header)
            return "header", updates
        if lowered.startswith("#date:"):
            value = stripped.split(":", 1)[1].strip() if ":" in stripped else ""
            header["date"] = value
            state["iis_header"] = header
            updates["iis_header"] = dict(header)
            return "header", updates
        return "comment", {}

    def build_context_attributes(self, state: dict[str, Any]) -> dict[str, Any]:
        attributes: dict[str, Any] = {}
        if "iis_fields" in state:
            attributes["iis_fields"] = tuple(state["iis_fields"])
        if "iis_header" in state:
            attributes["iis_header"] = dict(state["iis_header"])
        return attributes


class DocumentAdapter(StatelessLineAdapter):
    pass


@dataclass(slots=True)
class _SessionMutable:
    parser_name: str
    parser_version: str
    selected_by: Literal["explicit", "detection", "redetection"]
    detection_confidence: float | None
    detection_reason: str | None
    started_at_record: int
    records_attempted: int = 0
    records_succeeded: int = 0
    records_failed: int = 0
    ended_at_record: int | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


class ParserSession:
    """Owns active parser, state adapter, and per-record parse execution."""

    def __init__(
        self,
        parser_manager: ParserManager,
        *,
        parser_name: str,
        selected_by: Literal["explicit", "detection", "redetection"],
        started_at_record: int,
        options: BatchParseOptions,
        strategy: ParserRecordStrategy,
        base_context: ParserContext | None,
        detection_confidence: float | None = None,
        detection_reason: str | None = None,
    ) -> None:
        self._parser_manager = parser_manager
        registration = parser_manager.registry.get_registration(parser_name)
        self._strategy = strategy
        self._options = options
        self._base_context = base_context
        self._state: dict[str, Any] = {}
        self._mutable = _SessionMutable(
            parser_name=registration.parser_name,
            parser_version=registration.parser_version,
            selected_by=selected_by,
            detection_confidence=detection_confidence,
            detection_reason=detection_reason,
            started_at_record=started_at_record,
        )
        if strategy.mode == "stateful_line" and options.stateful_header_mode:
            self._adapter: ParserStateAdapter = IisW3CStateAdapter(parser_name)
        elif strategy.mode == "document":
            self._adapter = DocumentAdapter(parser_name)
        else:
            self._adapter = StatelessLineAdapter(parser_name)

    @property
    def parser_name(self) -> str:
        return self._mutable.parser_name

    def parse_item(
        self,
        source_record: SourceRecord,
        *,
        include_raw_record: bool,
        include_success_event: bool,
        include_failure_details: bool,
        source_id: str | None,
    ) -> BatchItemResult:
        item_type = self._adapter.classify_item(source_record)
        if item_type in {"blank", "header", "comment"}:
            status, updates = self._adapter.process_non_data_item(
                source_record, self._state
            )
            item = self._build_public_item(
                source_record,
                record_type=cast(
                    Literal["header", "comment", "blank"],
                    item_type,
                ),
                include_raw_record=include_raw_record,
            )
            return BatchItemResult(
                item=item,
                status=(
                    "skipped"
                    if status == "blank"
                    else cast(Literal["header", "comment"], status)
                ),
                parser_name=self._mutable.parser_name,
                state_updates=updates,
                attributes={"reason": item_type, "source_id": source_id},
            )

        started = perf_counter() if self._options.timing_enabled else None
        context = self.build_context_for_item(source_record, source_id=source_id)
        parse_result = self._parser_manager.parse_with(
            self._mutable.parser_name,
            source_record.raw or "",
            context,
        )
        duration_ms = None
        if started is not None:
            duration_ms = (perf_counter() - started) * 1000.0

        self._mutable.records_attempted += 1
        self._mutable.ended_at_record = source_record.index

        item = self._build_public_item(
            source_record, record_type="data", include_raw_record=include_raw_record
        )

        if parse_result_succeeded(parse_result):
            self._mutable.records_succeeded += 1
            event = (
                parse_result.events[0]
                if parse_result.events and include_success_event
                else None
            )
            return BatchItemResult(
                item=item,
                status="success",
                parser_name=self._mutable.parser_name,
                event=event,
                parse_result=parse_result,
                duration_ms=duration_ms,
            )

        self._mutable.records_failed += 1
        return BatchItemResult(
            item=item,
            status="failure",
            parser_name=self._mutable.parser_name,
            parse_result=parse_result,
            error_code=extract_error_code(parse_result),
            error_message=extract_error_message(
                parse_result,
                include_details=include_failure_details,
            ),
            duration_ms=duration_ms,
        )

    def build_context_for_item(
        self,
        item: SourceRecord,
        *,
        source_id: str | None,
    ) -> ParserContext:
        base = self._base_context or ParserContext()
        attributes = dict(base.attributes)
        attributes.update(self._adapter.build_context_attributes(self._state))
        attributes.update(
            {
                "batch_record_index": item.index,
                "source_line_start": item.line_start,
                "source_line_end": item.line_end,
                "batch_source_id": source_id,
                "batch_parser_session": self._mutable.parser_name,
            }
        )

        if self._options.parser_strict is not None:
            strict_value = self._options.parser_strict
        else:
            strict_value = base.strict

        return base.model_copy(
            update={
                "line_number": item.line_start,
                "attributes": attributes,
                "strict": strict_value,
            }
        )

    def snapshot(self, *, ended_at_record: int | None = None) -> ParserSessionInfo:
        if ended_at_record is not None:
            self._mutable.ended_at_record = ended_at_record
        return ParserSessionInfo(
            parser_name=self._mutable.parser_name,
            parser_version=self._mutable.parser_version,
            selected_by=self._mutable.selected_by,
            detection_confidence=self._mutable.detection_confidence,
            detection_reason=self._mutable.detection_reason,
            started_at_record=self._mutable.started_at_record,
            ended_at_record=self._mutable.ended_at_record,
            records_attempted=self._mutable.records_attempted,
            records_succeeded=self._mutable.records_succeeded,
            records_failed=self._mutable.records_failed,
            stateful=self._strategy.mode == "stateful_line",
            attributes=dict(self._mutable.attributes),
        )

    def _build_public_item(
        self,
        source_record: SourceRecord,
        *,
        record_type: Literal["data", "header", "comment", "blank", "document"],
        include_raw_record: bool,
    ) -> BatchItem:
        raw_record = source_record.raw if include_raw_record else None
        preview = source_record.preview
        return BatchItem(
            index=source_record.index,
            source_line_start=source_record.line_start,
            source_line_end=source_record.line_end,
            raw_record=raw_record,
            raw_record_preview=preview,
            record_type=record_type,
            context_attributes={},
            character_count=source_record.character_count,
        )
