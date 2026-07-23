import pytest
from pydantic import ValidationError

from log_parser_engine.models import ErrorType, ParseError, ParseStatus


def test_parse_error_defaults_and_serializes() -> None:
    error = ParseError(message="failed to parse")

    assert error.status == ParseStatus.failed
    assert error.error_type == ErrorType.unknown_format
    assert error.model_dump(mode="json")["status"] == "failed"
    assert error.model_dump(mode="json")["error_type"] == "unknown_format"


def test_parse_error_rejects_empty_message() -> None:
    with pytest.raises(ValidationError):
        ParseError(message="   ")
