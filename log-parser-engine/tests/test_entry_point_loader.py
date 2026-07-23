from __future__ import annotations

from types import SimpleNamespace

import pytest

from log_parser_engine.core import BaseParser, ParserContext
from log_parser_engine.exceptions import PluginLoadError
from log_parser_engine.models import (
    DetectionResult,
    ParseResult,
    ParserMetadata,
    PluginCandidate,
)
from log_parser_engine.plugins.entry_point_loader import EntryPointPluginLoader


class DummyParser(BaseParser):
    def __init__(self) -> None:
        super().__init__()
        self._metadata = ParserMetadata(
            name="json",
            display_name="Json",
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


def test_entry_point_loader_discovers_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_entry_points = [
        SimpleNamespace(
            name="json",
            module="demo_plugins.json_parser",
            attr="Parser",
            load=lambda: object(),
        )
    ]

    monkeypatch.setattr(
        "log_parser_engine.plugins.entry_point_loader.importlib.metadata.entry_points",
        lambda: {"log_parser_engine.parsers": fake_entry_points},
    )

    loader = EntryPointPluginLoader(group="log_parser_engine.parsers")
    candidates = loader.discover()

    assert len(candidates) == 1
    assert candidates[0].entry_point_name == "json"


def test_entry_point_loader_loads_candidate(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeEntryPoint:
        def __init__(self) -> None:
            self.name = "json"
            self.module = "demo_plugins.json_parser"
            self.attr = "Parser"

        def load(self) -> object:
            return DummyParser()

    monkeypatch.setattr(
        "log_parser_engine.plugins.entry_point_loader.importlib.metadata.entry_points",
        lambda: {"log_parser_engine.parsers": [FakeEntryPoint()]},
    )

    loader = EntryPointPluginLoader(group="log_parser_engine.parsers")
    candidate = loader.discover()[0]

    loaded = loader.load(candidate)

    assert loaded is not None


def test_entry_point_loader_rejects_unknown_candidate_source() -> None:
    candidate = PluginCandidate(
        name="json",
        source="package",
        module_name="demo_plugins.json_parser",
        origin="package:demo_plugins",
    )
    loader = EntryPointPluginLoader(group="log_parser_engine.parsers")

    with pytest.raises(PluginLoadError):
        loader.load(candidate)
