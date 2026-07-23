from __future__ import annotations

import pytest

from log_parser_engine.core import BaseParser, ParserContext
from log_parser_engine.exceptions import PluginFactoryError
from log_parser_engine.models import DetectionResult, ParseResult, ParserMetadata
from log_parser_engine.plugins.validation import resolve_parser_instance


class ExampleParser(BaseParser):
    def __init__(self) -> None:
        super().__init__()
        self._metadata = ParserMetadata(
            name="example",
            display_name="Example",
            version="1.0.0",
            source_type="application",
        )

    @property
    def metadata(self) -> ParserMetadata:
        return self._metadata

    def detect(
        self,
        raw_log: str,
        context: ParserContext | None = None,
    ) -> DetectionResult:
        return DetectionResult.no_match(self.name)

    def parse(self, raw_log: str, context: ParserContext | None = None) -> ParseResult:
        return ParseResult(status="success")


def test_resolve_parser_instance_accepts_parser_instance() -> None:
    parser = ExampleParser()

    resolved = resolve_parser_instance(parser)

    assert resolved is parser


def test_resolve_parser_instance_instantiates_subclass() -> None:
    resolved = resolve_parser_instance(ExampleParser)

    assert isinstance(resolved, ExampleParser)


def test_resolve_parser_instance_accepts_callable_factory() -> None:
    def factory() -> BaseParser:
        return ExampleParser()

    resolved = resolve_parser_instance(factory)

    assert isinstance(resolved, ExampleParser)


def test_resolve_parser_instance_rejects_invalid_factory() -> None:
    def bad_factory() -> int:
        return 1

    with pytest.raises(PluginFactoryError):
        resolve_parser_instance(bad_factory)
