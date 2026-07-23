from __future__ import annotations

from log_parser_engine.core import BaseParser, ParserContext
from log_parser_engine.models import (
    DetectionResult,
    ParseResult,
    ParserMetadata,
    PluginCandidate,
)
from log_parser_engine.plugins.plugin_discovery import PluginDiscovery


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


class StubLoader:
    def __init__(self, candidates: tuple[PluginCandidate, ...]) -> None:
        self._candidates = candidates
        self.source_name = "stub"

    def discover(self) -> tuple[PluginCandidate, ...]:
        return self._candidates

    def load(self, candidate: PluginCandidate) -> object:
        return DummyParser()


def test_plugin_discovery_uses_loaders_and_registry() -> None:
    candidate = PluginCandidate(
        name="json",
        source="package",
        module_name="demo_plugins.json_parser",
        origin="package:demo_plugins.json_parser",
    )
    discovery = PluginDiscovery(loaders=[StubLoader((candidate,))])

    result = discovery.discover_and_register(registry=None)  # type: ignore[arg-type]

    assert result.discovered_count == 1
    assert result.loaded_count == 1
