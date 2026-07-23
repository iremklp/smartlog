from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from io import StringIO
from pathlib import Path
from time import perf_counter
from typing import Any, Literal

from log_parser_engine.core import ParserContext, ParserManager
from log_parser_engine.exceptions.batch import (
    BatchConfigurationError,
    BatchDetectionError,
    BatchMixedFormatError,
    BatchProgressCallbackError,
    BatchRecordTooLargeError,
    BatchSourceError,
    BatchUnsupportedRecordModeError,
)
from log_parser_engine.models import (
    BatchItemResult,
    BatchParseResult,
    BatchParseStatistics,
    BatchProgress,
    ParserSelection,
)

from .buffering import DetectionSampleBuffer
from .error_policy import ErrorPolicyEvaluator
from .options import BatchParseOptions
from .parser_session import ParserSession
from .record_reader import (
    AutoRecordReader,
    LineRecordReader,
    MultilineDocumentReader,
    SourceRecord,
    iter_bounded_lines,
    iter_records_from_bounded_lines,
    open_text_stream,
)
from .state import ParserRecordStrategy, build_strategy_map
from .statistics import StatisticsTracker
from .stream import BatchParseStream


class BatchParseOrchestrator:
    """Synchronous, bounded-memory batch parser orchestration service."""

    def __init__(
        self,
        parser_manager: ParserManager,
        *,
        default_options: BatchParseOptions | None = None,
        strategies: dict[str, ParserRecordStrategy] | None = None,
    ) -> None:
        if not isinstance(parser_manager, ParserManager):
            raise TypeError("parser_manager must be a ParserManager")
        self._parser_manager = parser_manager
        self._default_options = default_options or BatchParseOptions()
        self._strategies = build_strategy_map(strategies)
        self._auto_reader = AutoRecordReader()

    def parse_text(
        self,
        text: str,
        *,
        context: ParserContext | None = None,
        options: BatchParseOptions | None = None,
    ) -> BatchParseResult:
        stream = self.iter_parse_text(text, context=context, options=options)
        return self._collect_stream(stream, options=options)

    def iter_parse_text(
        self,
        text: str,
        *,
        context: ParserContext | None = None,
        options: BatchParseOptions | None = None,
        progress_callback: Callable[[BatchProgress], None] | None = None,
    ) -> BatchParseStream:
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        resolved = self._resolve_options(options)

        def source_factory() -> Iterator[SourceRecord]:
            if resolved.record_mode == "multiline_document":
                reader = MultilineDocumentReader()
                return reader.iter_records([text], options=resolved)
            stream = StringIO(text)
            bounded = iter_bounded_lines(
                stream, max_characters=resolved.max_record_characters
            )
            return iter_records_from_bounded_lines(bounded)

        return self._build_stream(
            source_factory=source_factory,
            context=context,
            options=resolved,
            source_id=resolved.source_id,
            progress_callback=progress_callback,
            close_callback=None,
        )

    def parse_lines(
        self,
        lines: Iterable[str],
        *,
        context: ParserContext | None = None,
        options: BatchParseOptions | None = None,
    ) -> BatchParseResult:
        stream = self.iter_parse_lines(lines, context=context, options=options)
        return self._collect_stream(stream, options=options)

    def iter_parse_lines(
        self,
        lines: Iterable[str],
        *,
        context: ParserContext | None = None,
        options: BatchParseOptions | None = None,
        progress_callback: Callable[[BatchProgress], None] | None = None,
    ) -> BatchParseStream:
        if isinstance(lines, str):
            raise TypeError("lines must be an iterable of lines, not a string")
        resolved = self._resolve_options(options)

        def source_factory() -> Iterator[SourceRecord]:
            if resolved.record_mode == "multiline_document":
                return MultilineDocumentReader().iter_records(lines, options=resolved)
            return LineRecordReader().iter_records(lines, options=resolved)

        return self._build_stream(
            source_factory=source_factory,
            context=context,
            options=resolved,
            source_id=resolved.source_id,
            progress_callback=progress_callback,
            close_callback=None,
        )

    def iter_parse_path(
        self,
        path: str | Path,
        *,
        context: ParserContext | None = None,
        options: BatchParseOptions | None = None,
        encoding: str = "utf-8",
        encoding_errors: str = "strict",
        progress_callback: Callable[[BatchProgress], None] | None = None,
    ) -> BatchParseStream:
        resolved = self._resolve_options(options)
        handle = open_text_stream(
            path,
            encoding=encoding,
            errors=encoding_errors,
            follow_symlinks=resolved.follow_symlinks,
        )

        def source_factory() -> Iterator[SourceRecord]:
            bounded = iter_bounded_lines(
                handle, max_characters=resolved.max_record_characters
            )
            return iter_records_from_bounded_lines(bounded)

        return self._build_stream(
            source_factory=source_factory,
            context=context,
            options=resolved,
            source_id=resolved.source_id or str(Path(path)),
            progress_callback=progress_callback,
            close_callback=handle.close,
        )

    def _collect_stream(
        self,
        stream: BatchParseStream,
        *,
        options: BatchParseOptions | None,
    ) -> BatchParseResult:
        resolved = self._resolve_options(options)
        events: list[Any] = []
        failures: list[BatchItemResult] = []
        warnings: list[str] = []

        try:
            with stream:
                for item in stream:
                    if (
                        item.status == "success"
                        and item.event is not None
                        and resolved.collect_events
                    ):
                        if (
                            resolved.max_collected_events is None
                            or len(events) < resolved.max_collected_events
                        ):
                            events.append(item.event)
                        else:
                            warnings.append("events collection limit reached")
                    if item.status == "failure" and resolved.collect_failures:
                        if len(failures) < resolved.max_collected_failures:
                            failures.append(item)
                        else:
                            warnings.append("failure collection limit reached")
        except Exception as exc:  # noqa: BLE001
            if resolved.raise_fatal_errors:
                raise
            warnings.append(f"fatal stop: {exc.__class__.__name__}")

        statistics = stream.statistics
        return BatchParseResult(
            events=tuple(events),
            failures=tuple(failures),
            statistics=statistics,
            sessions=stream.sessions,
            warnings=tuple(warnings + list(stream.warnings)),
            source_id=resolved.source_id,
        )

    def _build_stream(
        self,
        *,
        source_factory: Callable[[], Iterator[SourceRecord]],
        context: ParserContext | None,
        options: BatchParseOptions,
        source_id: str | None,
        progress_callback: Callable[[BatchProgress], None] | None,
        close_callback: Callable[[], None] | None,
    ) -> BatchParseStream:
        stats = StatisticsTracker()
        warnings: list[str] = []
        sessions: list[Any] = []
        stop_reason: str | None = None
        started_at = perf_counter()

        def snapshot_statistics() -> BatchParseStatistics:
            stats.total_duration_ms = (
                (perf_counter() - started_at) * 1000.0
                if options.timing_enabled
                else 0.0
            )
            return stats.snapshot()

        def snapshot_sessions() -> tuple[Any, ...]:
            return tuple(sessions)

        def snapshot_warnings() -> tuple[str, ...]:
            return tuple(warnings)

        def get_stop_reason() -> str | None:
            return stop_reason

        def iterator_factory() -> Iterator[BatchItemResult]:
            nonlocal stop_reason
            source_iter = source_factory()
            policy = ErrorPolicyEvaluator(options)
            current_session: ParserSession | None = None
            detection_buffer = DetectionSampleBuffer(
                max_records=options.detection_sample_size,
                max_characters=options.max_detection_sample_characters,
            )
            buffered_items: list[SourceRecord] = []
            record_counter = 0

            try:
                for record in source_iter:
                    record_counter += 1
                    if (
                        options.max_records is not None
                        and record_counter > options.max_records
                    ):
                        stop_reason = "max_records"
                        stats.stopped_early = True
                        stats.stop_reason = stop_reason
                        break

                    if record.oversized:
                        result = self._oversized_result(record, options=options)
                        stats.observe_result(result)
                        yield result
                        decision = policy.evaluate_after_result(result)
                        if decision.stop:
                            stop_reason = decision.reason
                            stats.stopped_early = True
                            stats.stop_reason = stop_reason
                            if decision.exception_type is not None:
                                raise decision.exception_type(stop_reason)
                            raise BatchRecordTooLargeError(
                                record_index=record.index,
                                character_count=record.character_count,
                                max_characters=options.max_record_characters,
                            )
                        continue

                    if current_session is None and options.parser_name is not None:
                        current_session = self._create_session(
                            parser_name=options.parser_name,
                            selected_by="explicit",
                            start_record=record.index,
                            context=context,
                            options=options,
                            confidence=None,
                            reason="explicit parser",
                        )

                    if current_session is None and options.detect_once:
                        buffered_items.append(record)
                        detection_buffer.add(record)
                        if detection_buffer.item_count < options.detection_sample_size:
                            continue
                        current_session = self._detect_and_create_session(
                            detection_buffer,
                            context=context,
                            options=options,
                            start_record=buffered_items[0].index,
                        )
                        stats.parser_detection_count += 1

                        for buffered in buffered_items:
                            for yielded in self._process_record(
                                buffered,
                                session=current_session,
                                context=context,
                                options=options,
                                source_id=source_id,
                                stats=stats,
                                sessions=sessions,
                                warnings=warnings,
                            ):
                                yield yielded
                                decision = policy.evaluate_after_result(yielded)
                                if decision.stop:
                                    stop_reason = decision.reason
                                    stats.stopped_early = True
                                    stats.stop_reason = stop_reason
                                    if decision.exception_type is not None:
                                        raise decision.exception_type(stop_reason)
                                    raise BatchSourceError(stop_reason or "policy stop")
                                self._emit_progress(
                                    stats,
                                    current_session,
                                    source_id=source_id,
                                    options=options,
                                    progress_callback=progress_callback,
                                )
                        buffered_items.clear()
                        continue

                    if current_session is None and not options.detect_once:
                        current_session = self._detect_and_create_session_from_record(
                            record,
                            context=context,
                            options=options,
                        )
                        stats.parser_detection_count += 1

                    if current_session is None:
                        continue

                    for yielded in self._process_record(
                        record,
                        session=current_session,
                        context=context,
                        options=options,
                        source_id=source_id,
                        stats=stats,
                        sessions=sessions,
                        warnings=warnings,
                    ):
                        yield yielded
                        decision = policy.evaluate_after_result(yielded)
                        if decision.stop:
                            stop_reason = decision.reason
                            stats.stopped_early = True
                            stats.stop_reason = stop_reason
                            if decision.exception_type is not None:
                                raise decision.exception_type(stop_reason)
                            raise BatchSourceError(stop_reason or "policy stop")
                        self._emit_progress(
                            stats,
                            current_session,
                            source_id=source_id,
                            options=options,
                            progress_callback=progress_callback,
                        )

                if current_session is None and buffered_items and options.detect_once:
                    current_session = self._detect_and_create_session(
                        detection_buffer,
                        context=context,
                        options=options,
                        start_record=buffered_items[0].index,
                    )
                    stats.parser_detection_count += 1
                    for buffered in buffered_items:
                        for yielded in self._process_record(
                            buffered,
                            session=current_session,
                            context=context,
                            options=options,
                            source_id=source_id,
                            stats=stats,
                            sessions=sessions,
                            warnings=warnings,
                        ):
                            yield yielded
                            decision = policy.evaluate_after_result(yielded)
                            if decision.stop:
                                stop_reason = decision.reason
                                stats.stopped_early = True
                                stats.stop_reason = stop_reason
                                if decision.exception_type is not None:
                                    raise decision.exception_type(stop_reason)
                                raise BatchSourceError(stop_reason or "policy stop")
                            self._emit_progress(
                                stats,
                                current_session,
                                source_id=source_id,
                                options=options,
                                progress_callback=progress_callback,
                            )

                if current_session is not None:
                    sessions.append(
                        current_session.snapshot(ended_at_record=record_counter)
                    )

                self._emit_progress(
                    stats,
                    current_session,
                    source_id=source_id,
                    options=options,
                    progress_callback=progress_callback,
                    force=True,
                )
            except Exception as exc:  # noqa: BLE001
                stats.stopped_early = True
                if stop_reason is None:
                    stop_reason = exc.__class__.__name__
                stats.stop_reason = stop_reason
                if current_session is not None:
                    sessions.append(
                        current_session.snapshot(ended_at_record=record_counter)
                    )
                self._emit_progress(
                    stats,
                    current_session,
                    source_id=source_id,
                    options=options,
                    progress_callback=progress_callback,
                    force=True,
                )
                raise

            if record_counter == 0 and not options.allow_empty_source:
                stats.stopped_early = True
                stats.stop_reason = "empty_source"
                raise BatchSourceError("empty source is not allowed")

        return BatchParseStream(
            iterator_factory=iterator_factory,
            statistics_getter=snapshot_statistics,
            sessions_getter=snapshot_sessions,
            warnings_getter=snapshot_warnings,
            close_callback=close_callback,
            stop_reason_getter=get_stop_reason,
        )

    def _create_session(
        self,
        *,
        parser_name: str,
        selected_by: Literal["explicit", "detection", "redetection"],
        start_record: int,
        context: ParserContext | None,
        options: BatchParseOptions,
        confidence: float | None,
        reason: str | None,
    ) -> ParserSession:
        normalized = parser_name.strip().lower()
        if not self._parser_manager.registry.contains(normalized):
            raise BatchConfigurationError("requested parser is not registered")
        strategy = self._resolve_strategy(normalized, options)
        return ParserSession(
            self._parser_manager,
            parser_name=normalized,
            selected_by=selected_by,
            started_at_record=start_record,
            options=options,
            strategy=strategy,
            base_context=context,
            detection_confidence=confidence,
            detection_reason=reason,
        )

    def _resolve_strategy(
        self, parser_name: str, options: BatchParseOptions
    ) -> ParserRecordStrategy:
        strategy = self._strategies.get(parser_name)
        if strategy is not None:
            return strategy

        registration = self._parser_manager.registry.get_registration(parser_name)
        if registration.metadata.supports_multiline and options.record_mode == "auto":
            raise BatchUnsupportedRecordModeError(
                "unknown multiline parser requires explicit record_mode"
            )
        return ParserRecordStrategy(parser_name=parser_name, mode="line")

    def _detect_and_create_session(
        self,
        detection_buffer: DetectionSampleBuffer,
        *,
        context: ParserContext | None,
        options: BatchParseOptions,
        start_record: int,
    ) -> ParserSession:
        sample = detection_buffer.build_sample()
        if not sample.strip():
            raise BatchDetectionError("detection sample is empty")
        started = perf_counter()
        selection = self._parser_manager.select_parser(sample, context)
        duration_ms = (
            (perf_counter() - started) * 1000.0 if options.timing_enabled else 0.0
        )
        _ = duration_ms
        if not selection.selected or selection.parser_name is None:
            raise BatchDetectionError("no parser selected for detection sample")
        return self._create_session(
            parser_name=selection.parser_name,
            selected_by="detection",
            start_record=start_record,
            context=context,
            options=options,
            confidence=selection.confidence,
            reason=selection.reason,
        )

    def _detect_and_create_session_from_record(
        self,
        record: SourceRecord,
        *,
        context: ParserContext | None,
        options: BatchParseOptions,
    ) -> ParserSession:
        if record.raw is None or not record.raw.strip():
            raise BatchDetectionError("cannot detect parser from empty record")
        selection = self._parser_manager.select_parser(record.raw, context)
        if not selection.selected or selection.parser_name is None:
            raise BatchDetectionError("no parser selected for record")
        return self._create_session(
            parser_name=selection.parser_name,
            selected_by="detection",
            start_record=record.index,
            context=context,
            options=options,
            confidence=selection.confidence,
            reason=selection.reason,
        )

    def _process_record(
        self,
        record: SourceRecord,
        *,
        session: ParserSession,
        context: ParserContext | None,
        options: BatchParseOptions,
        source_id: str | None,
        stats: StatisticsTracker,
        sessions: list[Any],
        warnings: list[str],
    ) -> Iterator[BatchItemResult]:
        result = session.parse_item(
            record,
            include_raw_record=options.include_raw_record_in_result,
            include_success_event=options.include_success_event,
            include_failure_details=options.include_failure_details,
            source_id=source_id,
        )
        stats.observe_result(result)

        if (
            result.status == "success"
            and result.event is not None
            and options.collect_events
        ):
            if (
                options.max_collected_events is None
                or stats.events_collected < options.max_collected_events
            ):
                stats.events_collected += 1
        if result.status == "failure" and options.collect_failures:
            if stats.failures_collected < options.max_collected_failures:
                stats.failures_collected += 1
            else:
                stats.failures_dropped += 1

        if result.status == "failure" and options.redetect_on_failure:
            maybe_switched = self._attempt_redetection_switch(
                record,
                session=session,
                context=context,
                options=options,
                stats=stats,
                sessions=sessions,
            )
            if maybe_switched is not None:
                warnings.append("parser switched by redetection")
                yield maybe_switched
                return

        yield result

    def _attempt_redetection_switch(
        self,
        record: SourceRecord,
        *,
        session: ParserSession,
        context: ParserContext | None,
        options: BatchParseOptions,
        stats: StatisticsTracker,
        sessions: list[Any],
    ) -> BatchItemResult | None:
        if record.raw is None or not options.allow_mixed_formats:
            return None

        selection: ParserSelection = self._parser_manager.select_parser(
            record.raw, context
        )
        stats.parser_redetection_count += 1
        if not selection.selected or selection.parser_name is None:
            return None
        if selection.parser_name == session.parser_name:
            return None

        if not options.allow_mixed_formats:
            if options.strict:
                raise BatchMixedFormatError("mixed format detected and not allowed")
            return None

        sessions.append(session.snapshot(ended_at_record=record.index - 1))
        stats.parser_switch_count += 1
        new_session = self._create_session(
            parser_name=selection.parser_name,
            selected_by="redetection",
            start_record=record.index,
            context=context,
            options=options,
            confidence=selection.confidence,
            reason=selection.reason,
        )
        retry = new_session.parse_item(
            record,
            include_raw_record=options.include_raw_record_in_result,
            include_success_event=options.include_success_event,
            include_failure_details=options.include_failure_details,
            source_id=options.source_id,
        )
        retry = retry.model_copy(
            update={
                "detection_performed": True,
                "redetection_performed": True,
            }
        )
        return retry

    def _oversized_result(
        self,
        record: SourceRecord,
        *,
        options: BatchParseOptions,
    ) -> BatchItemResult:
        from log_parser_engine.models import BatchItem

        item = BatchItem(
            index=record.index,
            source_line_start=record.line_start,
            source_line_end=record.line_end,
            raw_record=None,
            raw_record_preview=record.preview,
            record_type="data",
            context_attributes={},
            character_count=record.character_count,
        )
        return BatchItemResult(
            item=item,
            status="failure",
            parser_name=None,
            parse_result=None,
            error_code="RECORD_TOO_LARGE",
            error_message="record exceeds max_record_characters",
            attributes={
                "max_record_characters": options.max_record_characters,
                "character_count": record.character_count,
            },
        )

    def _emit_progress(
        self,
        stats: StatisticsTracker,
        session: ParserSession | None,
        *,
        source_id: str | None,
        options: BatchParseOptions,
        progress_callback: Callable[[BatchProgress], None] | None,
        force: bool = False,
    ) -> None:
        if progress_callback is None:
            return
        if not force and stats.records_seen % options.progress_interval_records != 0:
            return
        snapshot = stats.snapshot()
        progress = BatchProgress(
            records_seen=snapshot.records_seen,
            records_succeeded=snapshot.records_succeeded,
            records_failed=snapshot.records_failed,
            records_skipped=snapshot.records_skipped,
            current_parser=session.parser_name if session is not None else None,
            elapsed_ms=snapshot.total_duration_ms,
            success_rate=snapshot.success_rate,
            error_rate=snapshot.error_rate,
            source_line=snapshot.records_seen if snapshot.records_seen > 0 else None,
            source_id=source_id,
        )
        try:
            progress_callback(progress)
        except Exception as exc:  # noqa: BLE001
            raise BatchProgressCallbackError("progress callback failed") from exc

    def _resolve_options(self, options: BatchParseOptions | None) -> BatchParseOptions:
        if options is None:
            return self._default_options
        if not isinstance(options, BatchParseOptions):
            raise TypeError("options must be BatchParseOptions")
        return options
