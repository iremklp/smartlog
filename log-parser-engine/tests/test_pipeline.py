from log_parser_engine.core import ParserContext, ParserManager, ParserRegistry
from log_parser_engine.models import LogSourceType, PipelineOptions
from log_parser_engine.normalization import LogNormalizer
from log_parser_engine.pipeline import LogProcessingPipeline, PipelineStage
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
