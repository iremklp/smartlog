import pytest
from pydantic import ValidationError

from log_parser_engine.models import PipelineStageResult
from log_parser_engine.pipeline import PipelineStage


def test_pipeline_stage_result_classmethods() -> None:
    success = PipelineStageResult.succeeded(
        stage=PipelineStage.PARSING,
        duration_ms=1.5,
    )
    assert success.success is True
    assert success.skipped is False
    assert success.terminal_failure is False

    failure = PipelineStageResult.failed(
        stage=PipelineStage.PARSING,
        duration_ms=2.0,
        error_type="parse_failed",
        message="bad",
    )
    assert failure.success is False
    assert failure.terminal_failure is True

    skipped = PipelineStageResult.skipped_result(
        stage=PipelineStage.NORMALIZATION,
        message="skipped",
    )
    assert skipped.success is True
    assert skipped.skipped is True


def test_pipeline_stage_result_validation_rules() -> None:
    with pytest.raises(ValidationError):
        PipelineStageResult(
            stage=PipelineStage.PARSING,
            success=False,
            duration_ms=1.0,
        )

    with pytest.raises(ValidationError):
        PipelineStageResult(
            stage=PipelineStage.PARSING,
            success=True,
            skipped=True,
            duration_ms=0.0,
            error_type="boom",
        )
