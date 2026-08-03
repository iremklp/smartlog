from typing import cast

import pytest

from log_parser_engine.core import ParserContext, ParserManager, ParserRegistry
from log_parser_engine.models import (
    ErrorType,
    LogSourceType,
    ParseResult,
    ParseStatus,
    PipelineOptions,
)
from log_parser_engine.normalization import LogNormalizer
from log_parser_engine.pipeline import PipelineStage
from log_parser_engine.pipeline.pipeline import LogProcessingPipeline
from tests.helpers.fake_parser import FakeParser


def test_pipeline_processes_single_log_successfully() -> None:
    parser = FakeParser(
        "fake",
        version="1.0.0",
        source_type=LogSourceType.application,
        matched=True,
        confidence=0.9,
        reason="match",
    )
    registry = ParserRegistry([parser])
    manager = ParserManager(registry, minimum_confidence=0.5, ambiguity_margin=0.01)
    pipeline = LogProcessingPipeline(manager, LogNormalizer())

    result = pipeline.process("hello world", context=ParserContext(application="api"))

    assert result.success is True
    assert result.event is not None
    assert result.parser_name == "fake"
    assert result.stages[-1].stage == PipelineStage.COMPLETED


def test_pipeline_fails_for_empty_input() -> None:
    parser = FakeParser("fake", matched=True, confidence=0.9)
    registry = ParserRegistry([parser])
    manager = ParserManager(registry)
    pipeline = LogProcessingPipeline(manager, LogNormalizer())

    result = pipeline.process("   ")

    assert result.success is False
    assert result.errors[0].error_type == "empty_input"
    assert result.stages[0].stage == PipelineStage.INPUT_VALIDATION


def test_pipeline_returns_structured_failure_for_non_string_input() -> None:
    parser = FakeParser("fake", matched=True, confidence=0.9)
    registry = ParserRegistry([parser])
    manager = ParserManager(registry)
    pipeline = LogProcessingPipeline(manager, LogNormalizer())

    result = pipeline.process(cast(str, None))

    assert result.success is False
    assert result.errors[0].error_type is ErrorType.EMPTY_INPUT
    assert result.errors[0].message == "raw_log must be a string"
    assert result.stages[0].stage == PipelineStage.INPUT_VALIDATION
    assert result.stages[0].success is False


@pytest.mark.parametrize("status", [ParseStatus.PARTIAL, ParseStatus.FAILED])
def test_pipeline_synthesizes_error_for_non_success_result_without_errors(
    status: ParseStatus,
) -> None:
    parser = FakeParser(
        "fake",
        matched=True,
        confidence=0.9,
        parse_result=ParseResult(status=status),
    )
    registry = ParserRegistry([parser])
    manager = ParserManager(registry)
    pipeline = LogProcessingPipeline(manager, LogNormalizer())

    result = pipeline.process("not successfully parsed")

    assert result.success is False
    assert len(result.errors) == 1
    assert result.errors[0].error_type is ErrorType.PARSE_FAILED
    assert result.parse_result is not None
    assert result.parse_result.status is status
    assert result.failed_stage is not None
    assert result.failed_stage.stage == PipelineStage.PARSING


def test_pipeline_uses_manual_parser_when_requested() -> None:
    parser = FakeParser("fake", matched=True, confidence=0.9)
    registry = ParserRegistry([parser])
    manager = ParserManager(registry)
    pipeline = LogProcessingPipeline(manager, LogNormalizer())

    result = pipeline.process(
        "hello",
        options=PipelineOptions(parser_name="FAKE", allow_disabled_parser=True),
    )

    assert result.success is True
    assert result.parser_name == "fake"
