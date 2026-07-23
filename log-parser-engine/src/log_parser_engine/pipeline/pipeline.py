from __future__ import annotations

import time

from log_parser_engine.core import BaseParser, ParserContext, ParserManager
from log_parser_engine.models import (
    ErrorType,
    LogEvent,
    LogSourceType,
    NormalizationResult,
    NormalizationWarning,
    ParseError,
    ParseResult,
    ParserSelection,
    ParseStatus,
    PipelineOptions,
    PipelineResult,
    PipelineStageResult,
)
from log_parser_engine.normalization import LogNormalizer

from .helpers import (
    build_normalization_input_from_parse_result,
    extract_event_from_parse_result,
)
from .stages import PipelineStage


class LogProcessingPipeline:
    """Orchestrate single-record parsing from raw log to structured event."""

    def __init__(
        self,
        parser_manager: ParserManager,
        normalizer: LogNormalizer,
    ) -> None:
        if not isinstance(parser_manager, ParserManager):
            raise TypeError("parser_manager must be a ParserManager")
        if not isinstance(normalizer, LogNormalizer):
            raise TypeError("normalizer must be a LogNormalizer")
        self._parser_manager = parser_manager
        self._normalizer = normalizer

    @property
    def parser_manager(self) -> ParserManager:
        return self._parser_manager

    @property
    def normalizer(self) -> LogNormalizer:
        return self._normalizer

    def process(
        self,
        raw_log: str,
        context: ParserContext | None = None,
        options: PipelineOptions | None = None,
    ) -> PipelineResult:
        if not isinstance(raw_log, str):
            return self._failure_result(
                error_type=ErrorType.EMPTY_INPUT,
                message="raw_log must be a string",
                duration_ms=0.0,
                stages=(),
            )
        if options is None:
            options = PipelineOptions()
        if not isinstance(options, PipelineOptions):
            raise TypeError("options must be a PipelineOptions")
        if context is not None and not isinstance(context, ParserContext):
            raise TypeError("context must be a ParserContext")

        started_at = time.perf_counter()
        stages: list[PipelineStageResult] = []

        cleaned_log = raw_log.strip()
        if not cleaned_log:
            stage = PipelineStageResult.failed(
                stage=PipelineStage.INPUT_VALIDATION,
                duration_ms=0.0,
                error_type=ErrorType.EMPTY_INPUT.value,
                message="raw_log must not be empty",
            )
            stages.append(stage)
            error = ParseError(
                message="raw_log must not be empty",
                status=ParseStatus.failed,
                error_type=ErrorType.EMPTY_INPUT,
                details={"stage": PipelineStage.INPUT_VALIDATION.value},
            )
            return self._failure_result(
                errors=(error,),
                duration_ms=self._duration_ms(started_at),
                stages=tuple(stages),
            )

        validation_stage = PipelineStageResult.succeeded(
            stage=PipelineStage.INPUT_VALIDATION,
            duration_ms=0.0,
            message="input validated",
            metadata={
                "raw_length": len(cleaned_log),
                "has_context": context is not None,
                "manual_parser_requested": options.manual_parser_requested,
            },
        )
        stages.append(validation_stage)

        selection: ParserSelection | None = None
        parser: BaseParser | None = None
        parse_result: ParseResult | None = None
        normalization_result: NormalizationResult | None = None
        warnings: list[NormalizationWarning] = []
        event: LogEvent | None = None

        if options.parser_name is not None:
            selection = None
            parser = self._get_manual_parser(
                options.parser_name,
                allow_disabled=options.allow_disabled_parser,
            )
            if parser is None:
                stage = PipelineStageResult.failed(
                    stage=PipelineStage.PARSER_SELECTION,
                    duration_ms=0.0,
                    error_type=ErrorType.DETECTION_FAILED.value,
                    message="selected parser was not found",
                )
                stages.append(stage)
                return self._failure_result(
                    errors=(self._parse_error_from_stage(stage, raw_log),),
                    duration_ms=self._duration_ms(started_at),
                    stages=tuple(stages),
                    parser_name=options.parser_name,
                )
        else:
            try:
                selection = self._parser_manager.select_parser(cleaned_log, context)
            except Exception as exc:  # noqa: BLE001
                stage = PipelineStageResult.failed(
                    stage=PipelineStage.PARSER_SELECTION,
                    duration_ms=0.0,
                    error_type=ErrorType.DETECTION_FAILED.value,
                    message=f"selection failed: {exc.__class__.__name__}",
                )
                stages.append(stage)
                return self._failure_result(
                    errors=(self._parse_error_from_stage(stage, raw_log),),
                    duration_ms=self._duration_ms(started_at),
                    stages=tuple(stages),
                )
            if (
                selection is None
                or not selection.selected
                or selection.parser_name is None
            ):
                stage = PipelineStageResult.failed(
                    stage=PipelineStage.PARSER_SELECTION,
                    duration_ms=0.0,
                    error_type=ErrorType.DETECTION_FAILED.value,
                    message=(
                        selection.reason
                        if selection is not None
                        else "no parser selected"
                    ),
                )
                stages.append(stage)
                return self._failure_result(
                    errors=(self._parse_error_from_stage(stage, raw_log),),
                    duration_ms=self._duration_ms(started_at),
                    stages=tuple(stages),
                )
            try:
                parser = self._parser_manager.registry.get(selection.parser_name)
            except Exception as exc:  # noqa: BLE001
                stage = PipelineStageResult.failed(
                    stage=PipelineStage.PARSER_SELECTION,
                    duration_ms=0.0,
                    error_type=ErrorType.INTERNAL_ERROR.value,
                    message=f"registry lookup failed: {exc.__class__.__name__}",
                )
                stages.append(stage)
                return self._failure_result(
                    errors=(self._parse_error_from_stage(stage, raw_log),),
                    duration_ms=self._duration_ms(started_at),
                    stages=tuple(stages),
                )

        selection_stage = PipelineStageResult.succeeded(
            stage=PipelineStage.PARSER_SELECTION,
            duration_ms=0.0,
            message="parser selected",
            metadata={
                "parser_name": parser.name if parser is not None else None,
                "selected": selection is not None and selection.selected,
                "ambiguous": selection.ambiguous if selection is not None else False,
            },
        )
        stages.append(selection_stage)

        if parser is None:
            stage = PipelineStageResult.failed(
                stage=PipelineStage.PARSING,
                duration_ms=0.0,
                error_type=ErrorType.INTERNAL_ERROR.value,
                message="no parser available",
            )
            stages.append(stage)
            return self._failure_result(
                errors=(self._parse_error_from_stage(stage, raw_log),),
                duration_ms=self._duration_ms(started_at),
                stages=tuple(stages),
            )

        parse_result = self._run_parser(parser, cleaned_log, context)
        if parse_result.status != ParseStatus.success:
            stage = PipelineStageResult.failed(
                stage=PipelineStage.PARSING,
                duration_ms=0.0,
                error_type=ErrorType.PARSE_FAILED.value,
                message="parser returned a failure result",
                metadata={"error_count": len(parse_result.errors)},
            )
            stages.append(stage)
            return self._failure_result(
                errors=tuple(parse_result.errors),
                duration_ms=self._duration_ms(started_at),
                stages=tuple(stages),
                parse_result=parse_result,
                parser_name=parser.name,
                parser_version=parser.version,
                source_type=parser.source_type,
                selection=selection,
            )

        parsing_stage = PipelineStageResult.succeeded(
            stage=PipelineStage.PARSING,
            duration_ms=0.0,
            message="parse completed",
            metadata={
                "event_count": len(parse_result.events),
                "error_count": len(parse_result.errors),
            },
        )
        stages.append(parsing_stage)

        if not options.normalize:
            event = extract_event_from_parse_result(parse_result)
            if event is None:
                stage = PipelineStageResult.failed(
                    stage=PipelineStage.NORMALIZATION,
                    duration_ms=0.0,
                    error_type=ErrorType.VALIDATION_FAILED.value,
                    message="parser did not produce a canonical event",
                )
                stages.append(stage)
                return self._failure_result(
                    errors=(self._parse_error_from_stage(stage, raw_log),),
                    duration_ms=self._duration_ms(started_at),
                    stages=tuple(stages),
                    parse_result=parse_result,
                    parser_name=parser.name,
                    parser_version=parser.version,
                    source_type=parser.source_type,
                    selection=selection,
                )
            skipped = PipelineStageResult.skipped_result(
                stage=PipelineStage.NORMALIZATION,
                message="normalization skipped by configuration",
            )
            stages.append(skipped)
            completed = PipelineStageResult.succeeded(
                stage=PipelineStage.COMPLETED,
                duration_ms=0.0,
                message="pipeline completed",
                metadata={"parser_name": parser.name, "normalized": False},
            )
            stages.append(completed)
            return PipelineResult.succeeded(
                event=event,
                duration_ms=self._duration_ms(started_at),
                parser_name=parser.name,
                parser_version=parser.version,
                source_type=parser.source_type,
                parse_result=parse_result,
                selection=selection,
                warnings=tuple(warnings),
                stages=tuple(stages),
                ambiguous=bool(selection is not None and selection.ambiguous),
                normalized=False,
            )

        event = extract_event_from_parse_result(parse_result)
        if event is not None:
            skipped = PipelineStageResult.skipped_result(
                stage=PipelineStage.NORMALIZATION,
                message="parser already returned a canonical LogEvent",
            )
            stages.append(skipped)
        else:
            normalization_input = build_normalization_input_from_parse_result(
                parse_result,
                raw_log=cleaned_log,
                parser=parser,
                context=context,
                options=options,
            )
            if normalization_input is None:
                stage = PipelineStageResult.failed(
                    stage=PipelineStage.NORMALIZATION,
                    duration_ms=0.0,
                    error_type=ErrorType.VALIDATION_FAILED.value,
                    message="normalization input could not be built",
                )
                stages.append(stage)
                return self._failure_result(
                    errors=(self._parse_error_from_stage(stage, raw_log),),
                    duration_ms=self._duration_ms(started_at),
                    stages=tuple(stages),
                    parse_result=parse_result,
                    parser_name=parser.name,
                    parser_version=parser.version,
                    source_type=parser.source_type,
                    selection=selection,
                )
            try:
                normalization_result = self._normalizer.normalize(
                    normalization_input,
                    context=context,
                )
            except Exception as exc:  # noqa: BLE001
                stage = PipelineStageResult.failed(
                    stage=PipelineStage.NORMALIZATION,
                    duration_ms=0.0,
                    error_type=ErrorType.VALIDATION_FAILED.value,
                    message=f"normalization failed: {exc.__class__.__name__}",
                )
                stages.append(stage)
                return self._failure_result(
                    errors=(self._parse_error_from_stage(stage, raw_log),),
                    duration_ms=self._duration_ms(started_at),
                    stages=tuple(stages),
                    parse_result=parse_result,
                    parser_name=parser.name,
                    parser_version=parser.version,
                    source_type=parser.source_type,
                    selection=selection,
                )
            event = normalization_result.event
            warnings.extend(normalization_result.warnings)

        completed = PipelineStageResult.succeeded(
            stage=PipelineStage.COMPLETED,
            duration_ms=0.0,
            message="pipeline completed",
            metadata={
                "parser_name": parser.name,
                "normalized": event is not None and normalization_result is not None,
            },
        )
        stages.append(completed)
        return PipelineResult.succeeded(
            event=event,
            duration_ms=self._duration_ms(started_at),
            parser_name=parser.name,
            parser_version=parser.version,
            source_type=parser.source_type,
            parse_result=parse_result,
            selection=selection,
            normalization_result=normalization_result,
            warnings=tuple(warnings),
            stages=tuple(stages),
            ambiguous=bool(selection is not None and selection.ambiguous),
            normalized=normalization_result is not None,
        )

    def _get_manual_parser(
        self,
        parser_name: str,
        *,
        allow_disabled: bool,
    ) -> BaseParser | None:
        registry = self._parser_manager.registry
        if not registry.contains(parser_name):
            return None
        parser = registry.get(parser_name)
        registration = registry.get_registration(parser_name)
        if not registration.enabled and not allow_disabled:
            return None
        return parser

    def _run_parser(
        self,
        parser: BaseParser,
        raw_log: str,
        context: ParserContext | None,
    ) -> ParseResult:
        try:
            return parser.safe_parse(raw_log, context)
        except Exception as exc:  # noqa: BLE001
            return ParseResult(
                status=ParseStatus.failed,
                errors=[
                    ParseError(
                        message=f"parser failed during parse: {exc.__class__.__name__}",
                        error_type=ErrorType.PARSE_FAILED,
                        status=ParseStatus.failed,
                    )
                ],
            )

    def _failure_result(
        self,
        *,
        errors: tuple[ParseError, ...] | None = None,
        duration_ms: float,
        stages: tuple[PipelineStageResult, ...],
        parse_result: ParseResult | None = None,
        parser_name: str | None = None,
        parser_version: str | None = None,
        source_type: LogSourceType | None = None,
        selection: ParserSelection | None = None,
        ambiguous: bool = False,
    ) -> PipelineResult:
        return PipelineResult.failed(
            errors=errors or tuple(),
            duration_ms=duration_ms,
            parse_result=parse_result,
            selection=selection,
            stages=stages,
            parser_name=parser_name,
            parser_version=parser_version,
            source_type=source_type,
            ambiguous=ambiguous,
        )

    def _parse_error_from_stage(
        self,
        stage: PipelineStageResult,
        raw_log: str,
    ) -> ParseError:
        return ParseError(
            message=stage.message or "pipeline failed",
            status=ParseStatus.failed,
            error_type=ErrorType.INTERNAL_ERROR,
            details={
                "stage": stage.stage.value,
                "error_type": stage.error_type or "unknown",
            },
        )

    def _duration_ms(self, started_at: float) -> float:
        return max(0.0, (time.perf_counter() - started_at) * 1000.0)
