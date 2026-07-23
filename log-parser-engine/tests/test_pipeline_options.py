import pytest
from pydantic import ValidationError

from log_parser_engine.models import PipelineOptions


def test_pipeline_options_defaults() -> None:
    options = PipelineOptions()

    assert options.parser_name is None
    assert options.normalize is True
    assert options.include_stage_results is True
    assert options.manual_parser_requested is False


def test_pipeline_options_trims_parser_name() -> None:
    options = PipelineOptions(parser_name="  nginx  ")

    assert options.parser_name == "nginx"


def test_pipeline_options_empty_parser_name_becomes_none() -> None:
    options = PipelineOptions(parser_name="   ")

    assert options.parser_name is None


def test_pipeline_options_confidence_override_validation() -> None:
    with pytest.raises(ValidationError):
        PipelineOptions(minimum_confidence_override=1.1)

    with pytest.raises(ValidationError):
        PipelineOptions(ambiguity_margin_override=-0.1)


def test_pipeline_options_max_raw_error_length_validation() -> None:
    with pytest.raises(ValidationError):
        PipelineOptions(max_raw_error_length=0)


def test_pipeline_options_is_immutable() -> None:
    options = PipelineOptions()

    with pytest.raises(ValidationError):
        options.parser_name = "x"  # type: ignore[misc]
