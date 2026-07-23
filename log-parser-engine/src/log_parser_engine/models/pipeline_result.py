from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from log_parser_engine.pipeline.stages import PipelineStage

from .enums import LogSourceType, ParseStatus
from .log_event import LogEvent
from .normalization import NormalizationResult, NormalizationWarning
from .parse_error import ParseError
from .parse_result import ParseResult
from .parser_selection import ParserSelection
from .pipeline_stage_result import PipelineStageResult


class PipelineResult(BaseModel):
    """Immutable outcome of a full processing pipeline run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    success: bool
    event: LogEvent | None = None
    parse_result: ParseResult | None = None
    normalization_result: NormalizationResult | None = None
    selection: ParserSelection | None = None
    errors: tuple[ParseError, ...] = Field(default_factory=tuple)
    warnings: tuple[NormalizationWarning, ...] = Field(default_factory=tuple)
    stages: tuple[PipelineStageResult, ...] = Field(default_factory=tuple)
    duration_ms: float
    parser_name: str | None = None
    parser_version: str | None = None
    source_type: LogSourceType | None = None
    ambiguous: bool = False
    normalized: bool = False

    @field_validator("duration_ms")
    @classmethod
    def validate_duration(cls, value: float) -> float:
        if value < 0:
            raise ValueError("duration_ms must not be negative")
        return value

    @field_validator("parser_name", "parser_version")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def validate_rules(self) -> "PipelineResult":
        if self.success:
            if self.event is None:
                raise ValueError("successful results must include an event")
            if self.errors:
                raise ValueError("successful results must not include errors")
            if self.parser_name is None and self.parser_version is not None:
                raise ValueError("parser_version requires a parser_name")
            if self.normalized and self.normalization_result is None:
                raise ValueError("normalized results must include normalization_result")
            if (
                self.parse_result is not None
                and self.parse_result.status == ParseStatus.failed
            ):
                raise ValueError("parse_result failure is incompatible with success")
        else:
            if self.event is not None:
                raise ValueError("failed results must not include an event")
            if not self.errors:
                raise ValueError("failed results must include at least one error")
            if self.parser_name is None and self.parser_version is not None:
                raise ValueError("parser_version requires a parser_name")
            if self.ambiguous and self.selection is None:
                raise ValueError("ambiguous results require a selection")
            if (
                self.ambiguous
                and self.selection is not None
                and not self.selection.ambiguous
            ):
                raise ValueError("selection must be ambiguous")
            if self.normalized and self.normalization_result is None:
                raise ValueError("normalized results must include normalization_result")
        if self.stages:
            stage_names = [stage.stage for stage in self.stages]
            if len(stage_names) != len(set(stage_names)):
                raise ValueError("stages must be unique")
            ordered = [stage.stage for stage in self.stages]
            expected = [
                PipelineStage.INPUT_VALIDATION,
                PipelineStage.PARSER_SELECTION,
                PipelineStage.PARSING,
                PipelineStage.NORMALIZATION,
                PipelineStage.COMPLETED,
            ]
            stage_positions = {stage: index for index, stage in enumerate(expected)}
            for stage in ordered:
                if stage not in stage_positions:
                    raise ValueError("invalid stage order")
            if ordered != [stage for stage in ordered if stage in expected]:
                pass
            for index, stage in enumerate(ordered[1:], start=1):
                if stage_positions[stage] < stage_positions[ordered[index - 1]]:
                    raise ValueError("stage order does not follow pipeline flow")
        if self.success and self.stages:
            if PipelineStage.COMPLETED not in [stage.stage for stage in self.stages]:
                raise ValueError("successful results must include a completed stage")
        return self

    @classmethod
    def succeeded(
        cls,
        *,
        event: LogEvent,
        duration_ms: float,
        parser_name: str | None,
        parser_version: str | None,
        source_type: LogSourceType | None,
        parse_result: ParseResult,
        selection: ParserSelection | None,
        normalization_result: NormalizationResult | None = None,
        warnings: tuple[NormalizationWarning, ...] = (),
        stages: tuple[PipelineStageResult, ...] = (),
        ambiguous: bool = False,
        normalized: bool = False,
    ) -> "PipelineResult":
        return cls(
            success=True,
            event=event,
            parse_result=parse_result,
            normalization_result=normalization_result,
            selection=selection,
            warnings=warnings,
            stages=stages,
            duration_ms=duration_ms,
            parser_name=parser_name,
            parser_version=parser_version,
            source_type=source_type,
            ambiguous=ambiguous,
            normalized=normalized,
        )

    @classmethod
    def failed(
        cls,
        *,
        errors: tuple[ParseError, ...],
        duration_ms: float,
        parse_result: ParseResult | None = None,
        selection: ParserSelection | None = None,
        normalization_result: NormalizationResult | None = None,
        warnings: tuple[NormalizationWarning, ...] = (),
        stages: tuple[PipelineStageResult, ...] = (),
        parser_name: str | None = None,
        parser_version: str | None = None,
        source_type: LogSourceType | None = None,
        ambiguous: bool = False,
    ) -> "PipelineResult":
        return cls(
            success=False,
            parse_result=parse_result,
            normalization_result=normalization_result,
            selection=selection,
            errors=errors,
            warnings=warnings,
            stages=stages,
            duration_ms=duration_ms,
            parser_name=parser_name,
            parser_version=parser_version,
            source_type=source_type,
            ambiguous=ambiguous,
        )

    @property
    def has_warnings(self) -> bool:
        return bool(self.warnings)

    @property
    def failed_stage(self) -> PipelineStageResult | None:
        return next(
            (stage for stage in reversed(self.stages) if not stage.success),
            None,
        )

    @property
    def parser_identifier(self) -> str | None:
        if self.parser_name is None or self.parser_version is None:
            return None
        return f"{self.parser_name}@{self.parser_version}"

    @property
    def completed_stages(self) -> tuple[PipelineStage, ...]:
        return tuple(stage.stage for stage in self.stages)
