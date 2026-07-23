import pytest
from pydantic import ValidationError

from log_parser_engine.core import ParserContext


def test_parser_context_defaults() -> None:
    context = ParserContext()
    assert context.encoding == "utf-8"
    assert context.strict is False
    assert context.preserve_raw is True


def test_parser_context_normalizes_texts() -> None:
    context = ParserContext(
        source_name="  app  ",
        file_path="  /tmp/log.txt  ",
        environment="  prod  ",
        application="  api  ",
        service="  web  ",
        host="  host1  ",
        content_type="  Application/JSON  ",
    )

    assert context.source_name == "app"
    assert context.file_path == "/tmp/log.txt"
    assert context.content_type == "application/json"


def test_parser_context_rejects_empty_encoding() -> None:
    with pytest.raises(ValidationError):
        ParserContext(encoding="   ")


def test_parser_context_with_line_number_returns_copy() -> None:
    context = ParserContext()
    clone = context.with_line_number(42)

    assert clone.line_number == 42
    assert context.line_number is None


def test_parser_context_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ParserContext(extra_field="value")  # type: ignore[call-arg]
