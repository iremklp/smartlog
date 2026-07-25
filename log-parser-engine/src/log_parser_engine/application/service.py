from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Literal, cast

from log_parser_engine.batch import BatchParseOptions
from log_parser_engine.core import ParserContext
from log_parser_engine.exceptions import AnalysisConcurrencyLimitError
from log_parser_engine.models import (
    BatchParseResult,
    BatchWriteResult,
    EventAggregationRequest,
    EventAggregationResult,
    EventQuery,
    EventQueryResult,
    EventStoreStatistics,
    EventWriteResult,
    IngestionResult,
    LogEvent,
    ParseResult,
    ParserRegistration,
    PipelineOptions,
    PipelineResult,
    StoredEvent,
)
from log_parser_engine.storage import (
    BatchWriteOptions,
    EventStore,
    EventWriteOptions,
)

from .commands import AnalyzeEventsCommand, CompareEventsCommand
from .container import ApplicationContainer
from .health import ApplicationHealth
from .helpers import build_parser_context
from .responses import AnalyzeEventsResponse, CompareEventsResponse
from .runtime_statistics import ApplicationRuntimeStatistics


class LogAnalysisApplicationService:
    """Application boundary above ingestion, parsing, batch, and store subsystems."""

    def __init__(self, container: ApplicationContainer) -> None:
        if not isinstance(container, ApplicationContainer):
            raise TypeError("container must be an ApplicationContainer")
        self._container = container

    @property
    def container(self) -> ApplicationContainer:
        return self._container

    @property
    def store(self) -> EventStore:
        return self._container.store

    def health(self) -> ApplicationHealth:
        store_stats = self._container.store_statistics()
        checked_at = datetime.now(timezone.utc)
        warnings = self._container.startup_warnings
        status: Literal["healthy", "degraded"] = (
            "healthy" if not warnings else "degraded"
        )
        return ApplicationHealth(
            status=status,
            created_at=self._container.created_at,
            checked_at=checked_at,
            uptime_ms=(
                checked_at - self._container.created_at
            ).total_seconds()
            * 1000.0,
            parser_count=self._container.registry.count,
            enabled_parser_count=self._container.registry.enabled_count,
            store_event_count=store_stats.event_count,
            warnings=warnings,
        )

    def runtime_statistics(self) -> ApplicationRuntimeStatistics:
        observed_at = datetime.now(timezone.utc)
        analysis_metrics = self._container.analysis_runtime_metrics.snapshot()
        return ApplicationRuntimeStatistics(
            created_at=self._container.created_at,
            observed_at=observed_at,
            uptime_ms=(
                observed_at - self._container.created_at
            ).total_seconds()
            * 1000.0,
            parser_count=self._container.registry.count,
            enabled_parser_count=self._container.registry.enabled_count,
            store_statistics=self._container.store_statistics(),
            startup_warnings=self._container.startup_warnings,
            **analysis_metrics,
        )

    def analyze_events(
        self,
        command: AnalyzeEventsCommand,
    ) -> AnalyzeEventsResponse:
        if not isinstance(command, AnalyzeEventsCommand):
            raise TypeError("command must be an AnalyzeEventsCommand")
        started = perf_counter()
        if not self._container.try_acquire_analysis_slot():
            self._container.analysis_runtime_metrics.record_analysis(
                event_count=0,
                duration_ms=(perf_counter() - started) * 1000.0,
                failed=True,
            )
            raise AnalysisConcurrencyLimitError(
                self._container.options.max_concurrent_analysis_operations
            )
        try:
            events = self._container.store.snapshot_events()
            result = self._container.analysis_engine.analyze(events, command.request)
        except Exception:
            duration_ms = (perf_counter() - started) * 1000.0
            self._container.analysis_runtime_metrics.record_analysis(
                event_count=0,
                duration_ms=duration_ms,
                failed=True,
            )
            raise
        finally:
            self._container.release_analysis_slot()
        self._container.analysis_runtime_metrics.record_analysis(
            event_count=result.matched_event_count,
            duration_ms=result.analysis_duration_ms,
        )
        return AnalyzeEventsResponse(result=result)

    def compare_events(
        self,
        command: CompareEventsCommand,
    ) -> CompareEventsResponse:
        if not isinstance(command, CompareEventsCommand):
            raise TypeError("command must be a CompareEventsCommand")
        started = perf_counter()
        if not self._container.try_acquire_analysis_slot():
            self._container.analysis_runtime_metrics.record_comparison(
                event_count=0,
                duration_ms=(perf_counter() - started) * 1000.0,
                failed=True,
            )
            raise AnalysisConcurrencyLimitError(
                self._container.options.max_concurrent_analysis_operations
            )
        try:
            events = self._container.store.snapshot_events()
            result = self._container.analysis_engine.compare(
                events,
                events,
                command.request,
            )
        except Exception:
            duration_ms = (perf_counter() - started) * 1000.0
            self._container.analysis_runtime_metrics.record_comparison(
                event_count=0,
                duration_ms=duration_ms,
                failed=True,
            )
            raise
        finally:
            self._container.release_analysis_slot()
        self._container.analysis_runtime_metrics.record_comparison(
            event_count=(
                result.baseline_event_count + result.comparison_event_count
            ),
            duration_ms=result.duration_ms,
        )
        return CompareEventsResponse(result=result)

    def list_parsers(
        self,
        *,
        enabled_only: bool = False,
    ) -> tuple[ParserRegistration, ...]:
        return self._container.registry.list_registrations(enabled_only=enabled_only)

    def ingest_text(
        self,
        text: str,
        *,
        source_name: str | None = None,
    ) -> IngestionResult:
        return self._container.ingestion_service.ingest_text(
            text,
            source_name=source_name,
        )

    def ingest_bytes(
        self,
        data: bytes,
        *,
        source_name: str | None = None,
    ) -> IngestionResult:
        return self._container.ingestion_service.ingest_bytes(
            data,
            source_name=source_name,
        )

    def ingest_path(self, path: str | Path) -> IngestionResult:
        return self._container.ingestion_service.ingest_path(path)

    def parse_text(
        self,
        raw_log: str,
        *,
        context: ParserContext | None = None,
        options: PipelineOptions | None = None,
    ) -> PipelineResult:
        resolved_context = build_parser_context(context)
        return cast(
            PipelineResult,
            self._container.pipeline.process(
                raw_log,
                context=resolved_context,
                options=options,
            ),
        )

    def parse_with_parser(
        self,
        parser_name: str,
        raw_log: str,
        *,
        context: ParserContext | None = None,
        allow_disabled_parser: bool = False,
    ) -> ParseResult:
        resolved_context = build_parser_context(context)
        return self._container.parser_manager.parse_with(
            parser_name,
            raw_log,
            resolved_context,
            allow_disabled=allow_disabled_parser,
        )

    def parse_and_store_text(
        self,
        raw_log: str,
        *,
        context: ParserContext | None = None,
        options: PipelineOptions | None = None,
        write_options: EventWriteOptions | None = None,
    ) -> EventWriteResult:
        pipeline_result = self.parse_text(raw_log, context=context, options=options)
        event = self._require_event_from_pipeline_result(pipeline_result)
        return self.add_event(event, options=write_options)

    def batch_parse_text(
        self,
        text: str,
        *,
        context: ParserContext | None = None,
        options: BatchParseOptions | None = None,
    ) -> BatchParseResult:
        resolved_context = build_parser_context(context)
        return self._container.batch_orchestrator.parse_text(
            text,
            context=resolved_context,
            options=options,
        )

    def batch_parse_lines(
        self,
        lines: Iterable[str],
        *,
        context: ParserContext | None = None,
        options: BatchParseOptions | None = None,
    ) -> BatchParseResult:
        resolved_context = build_parser_context(context)
        return self._container.batch_orchestrator.parse_lines(
            lines,
            context=resolved_context,
            options=options,
        )

    def batch_parse_and_store_text(
        self,
        text: str,
        *,
        context: ParserContext | None = None,
        options: BatchParseOptions | None = None,
        batch_write_options: BatchWriteOptions | None = None,
    ) -> BatchWriteResult:
        result = self.batch_parse_text(text, context=context, options=options)
        return self.add_many_events(
            result.events,
            batch_options=batch_write_options,
        )

    def add_event(
        self,
        event: LogEvent,
        *,
        options: EventWriteOptions | None = None,
    ) -> EventWriteResult:
        return self._container.store.add(event, options=options)

    def add_many_events(
        self,
        events: Iterable[LogEvent],
        *,
        options: EventWriteOptions | None = None,
        batch_options: BatchWriteOptions | None = None,
    ) -> BatchWriteResult:
        return self._container.store.add_many(
            events,
            options=options,
            batch_options=batch_options,
        )

    def get_event(self, event_id: str) -> StoredEvent | None:
        return self._container.store.get(event_id)

    def delete_event(self, event_id: str) -> bool:
        return self._container.store.delete(event_id)

    def clear_events(self) -> int:
        return self._container.store.clear()

    def query_events(self, query: EventQuery | None = None) -> EventQueryResult:
        return self._container.store.query(query)

    def aggregate_events(
        self,
        request: EventAggregationRequest,
        *,
        base_query: EventQuery | None = None,
    ) -> EventAggregationResult | None:
        query = base_query or EventQuery(
            include_events=False,
            include_total=False,
            aggregation=request,
        )
        if query.aggregation != request:
            query = query.model_copy(update={"aggregation": request})
        return self._container.store.query(query).aggregation

    def store_statistics(self) -> EventStoreStatistics:
        return self._container.store.statistics()

    def _require_event_from_pipeline_result(
        self,
        result: PipelineResult,
    ) -> LogEvent:
        if not result.success or result.event is None:
            raise ValueError("pipeline result did not produce a canonical event")
        return result.event
