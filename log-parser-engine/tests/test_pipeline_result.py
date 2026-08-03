from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from log_parser_engine.models import (
    LogEvent,
    LogSourceType,
    ParseResult,
    ParseStatus,
    PipelineResult,
    PipelineStageResult,
)
from log_parser_engine.pipeline import PipelineStage


def test_pipeline_result_succeeded_and_properties() -> None:
    event = LogEvent(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        source_type=LogSourceType.application,
        message="hello",
        raw_message="hello",
    )
    parse_result = ParseResult(status=ParseStatus.success, events=[event])
    result = PipelineResult.succeeded(
        event=event,
        duration_ms=3.0,
        parser_name="fake",
        parser_version="1.0.0",
        source_type=LogSourceType.application,
        parse_result=parse_result,
        selection=None,
        stages=(
            PipelineStageResult.succeeded(
                stage=PipelineStage.INPUT_VALIDATION,
                duration_ms=0.1,
            ),
            PipelineStageResult.succeeded(
                stage=PipelineStage.PARSER_SELECTION,
                duration_ms=0.1,
            ),
            PipelineStageResult.succeeded(
                stage=PipelineStage.PARSING,
                duration_ms=0.1,
            ),
            PipelineStageResult.succeeded(
                stage=PipelineStage.NORMALIZATION,
                duration_ms=0.1,
            ),
            PipelineStageResult.succeeded(
                stage=PipelineStage.COMPLETED,
                duration_ms=0.1,
            ),
        ),
    )

    assert result.success is True
    assert result.parser_identifier == "fake@1.0.0"
    assert result.completed_stages == (
        PipelineStage.INPUT_VALIDATION,
        PipelineStage.PARSER_SELECTION,
        PipelineStage.PARSING,
        PipelineStage.NORMALIZATION,
        PipelineStage.COMPLETED,
    )


def test_pipeline_result_failed_validation() -> None:
    with pytest.raises(ValidationError):
        PipelineResult.failed(
            errors=tuple(),
            duration_ms=1.0,
        )
