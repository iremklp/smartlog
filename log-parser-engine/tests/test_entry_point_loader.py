from __future__ import annotations

from types import SimpleNamespace
from typing import NoReturn

import pytest

from log_parser_engine.core import BaseParser, ParserContext
from log_parser_engine.exceptions import PluginDiscoveryError, PluginLoadError
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


def patch_entry_points(
    monkeypatch: pytest.MonkeyPatch,
    entry_points: list[object],
    *,
    group: str = "log_parser_engine.parsers",
) -> None:
    monkeypatch.setattr(
        "log_parser_engine.plugins.entry_point_loader."
        "importlib_metadata.entry_points",
        lambda: {group: entry_points},
    )


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

    patch_entry_points(monkeypatch, fake_entry_points)

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

    patch_entry_points(monkeypatch, [FakeEntryPoint()])

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


def test_entry_point_loader_name_allowlist_filters_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_entry_points = [
        SimpleNamespace(
            name="redis",
            module="demo_plugins.redis_parser",
            attr="Parser",
        ),
        SimpleNamespace(
            name="json",
            module="demo_plugins.json_parser",
            attr="Parser",
        ),
    ]
    patch_entry_points(monkeypatch, fake_entry_points)
    loader = EntryPointPluginLoader(name_allowlist=("json",))

    candidates = loader.discover()

    assert [candidate.entry_point_name for candidate in candidates] == ["json"]


def test_entry_point_loader_empty_allowlist_discovers_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_entry_points(
        monkeypatch,
        [
            SimpleNamespace(
                name="json",
                module="demo_plugins.json_parser",
                attr="Parser",
            )
        ],
    )

    candidates = EntryPointPluginLoader(name_allowlist=()).discover()

    assert candidates == ()


def test_entry_point_loader_uses_full_deterministic_sort_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_entry_points = [
        SimpleNamespace(name="same", module="z_plugins.parser", attr="Factory"),
        SimpleNamespace(name="zeta", module="a_plugins.parser", attr="Parser"),
        SimpleNamespace(name="same", module="a_plugins.parser", attr="Parser"),
        SimpleNamespace(name="Alpha", module="z_plugins.parser", attr="Parser"),
        SimpleNamespace(name="alpha", module="a_plugins.parser", attr="Parser"),
    ]
    patch_entry_points(monkeypatch, fake_entry_points)

    candidates = EntryPointPluginLoader().discover()

    assert [
        (
            candidate.entry_point_name,
            candidate.module_name,
            candidate.object_name,
        )
        for candidate in candidates
    ] == [
        ("Alpha", "z_plugins.parser", "Parser"),
        ("alpha", "a_plugins.parser", "Parser"),
        ("same", "a_plugins.parser", "Parser"),
        ("same", "z_plugins.parser", "Factory"),
        ("zeta", "a_plugins.parser", "Parser"),
    ]


@pytest.mark.parametrize(
    "group",
    (
        "",
        " ",
        ".log_parser_engine.parsers",
        "log_parser_engine..parsers",
        "log parser engine.parsers",
        "log-parser-engine.parsers",
    ),
)
def test_entry_point_loader_rejects_invalid_group(group: str) -> None:
    with pytest.raises(ValueError, match="valid dotted identifier"):
        EntryPointPluginLoader(group=group)


def test_entry_point_loader_rejects_invalid_discovered_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_entry_points(
        monkeypatch,
        [
            SimpleNamespace(
                name="invalid name",
                module="demo_plugins.json_parser",
                attr="Parser",
            )
        ],
    )

    with pytest.raises(PluginDiscoveryError, match="metadata is invalid"):
        EntryPointPluginLoader().discover()


def test_entry_point_loader_rejects_candidate_from_different_group() -> None:
    candidate = PluginCandidate(
        name="json",
        source="entry_point",
        module_name="demo_plugins.json_parser",
        object_name="Parser",
        entry_point_group="other.parsers",
        entry_point_name="json",
        origin="entry_point:other.parsers:json",
    )

    with pytest.raises(PluginLoadError, match="group is invalid"):
        EntryPointPluginLoader().load(candidate)


def test_entry_point_loader_rejects_candidate_outside_name_allowlist() -> None:
    candidate = PluginCandidate(
        name="redis",
        source="entry_point",
        module_name="demo_plugins.redis_parser",
        object_name="Parser",
        entry_point_group="log_parser_engine.parsers",
        entry_point_name="redis",
        origin="entry_point:log_parser_engine.parsers:redis",
    )

    with pytest.raises(PluginLoadError, match="not allowed"):
        EntryPointPluginLoader(name_allowlist=("json",)).load(candidate)


def test_entry_point_loader_does_not_leak_raw_load_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingEntryPoint:
        name = "json"
        module = "demo_plugins.json_parser"
        attr = "Parser"

        def load(self) -> NoReturn:
            raise RuntimeError("secret=/private/internal/plugin.py")

    patch_entry_points(monkeypatch, [FailingEntryPoint()])
    loader = EntryPointPluginLoader()
    candidate = loader.discover()[0]

    with pytest.raises(PluginLoadError) as captured:
        loader.load(candidate)

    error_message = str(captured.value)
    assert error_message == "entry point load failed"
    assert "secret" not in error_message
    assert "/private/" not in error_message
