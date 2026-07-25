from __future__ import annotations

from typing import cast

import pytest

from log_parser_engine.core import ParserRegistry
from log_parser_engine.exceptions import (
    ParserAlreadyRegisteredError,
    PluginDiscoveryError,
)
from log_parser_engine.models import PluginCandidate
from log_parser_engine.plugins.base_loader import BasePluginLoader
from log_parser_engine.plugins.plugin_discovery import PluginDiscovery
from tests.helpers.fake_parser import FakeParser


def _candidate(
    name: str,
    module_name: str,
    *,
    source: str = "package",
) -> PluginCandidate:
    return PluginCandidate(
        name=name,
        source=source,
        module_name=module_name,
        origin=f"{source}:{module_name}",
    )


class StubLoader(BasePluginLoader):
    def __init__(
        self,
        candidates: tuple[PluginCandidate, ...],
        *,
        source_name: str = "stub",
        versions: dict[str, str] | None = None,
        discover_error: Exception | None = None,
        load_error_modules: frozenset[str] = frozenset(),
    ) -> None:
        self._candidates = candidates
        self._source_name = source_name
        self._versions = dict(versions or {})
        self._discover_error = discover_error
        self._load_error_modules = load_error_modules
        self.discover_calls = 0
        self.load_calls: list[str] = []

    @property
    def source_name(self) -> str:
        return self._source_name

    def discover(self) -> tuple[PluginCandidate, ...]:
        self.discover_calls += 1
        if self._discover_error is not None:
            raise self._discover_error
        return self._candidates

    def load(self, candidate: PluginCandidate) -> object:
        self.load_calls.append(candidate.module_name)
        if candidate.module_name in self._load_error_modules:
            raise RuntimeError("secret loader detail must not escape")
        return FakeParser(
            candidate.name,
            version=self._versions.get(candidate.module_name, "1.0.0"),
        )


class SafeOnlyLoader(StubLoader):
    def __init__(self, candidate: PluginCandidate) -> None:
        super().__init__((candidate,), source_name="safe-only")
        self.safe_discover_calls = 0
        self.safe_load_calls = 0

    def discover(self) -> tuple[PluginCandidate, ...]:
        raise AssertionError("discover must not be called directly")

    def load(self, candidate: PluginCandidate) -> object:
        raise AssertionError("load must not be called directly")

    def safe_discover(self) -> tuple[PluginCandidate, ...]:
        self.safe_discover_calls += 1
        return self._candidates

    def safe_load(self, candidate: PluginCandidate) -> object:
        self.safe_load_calls += 1
        return FakeParser(candidate.name)


def test_plugin_discovery_uses_loader_safe_methods_directly() -> None:
    candidate = _candidate("json", "demo_plugins.json_parser")
    loader = SafeOnlyLoader(candidate)

    result = PluginDiscovery(loaders=[loader]).discover_and_register()

    assert result.loaded_count == 1
    assert result.registered_count == 0
    assert loader.safe_discover_calls == 1
    assert loader.safe_load_calls == 1


def test_plugin_discovery_validates_loaders_and_candidate_limit() -> None:
    invalid_loader = cast(BasePluginLoader, object())

    with pytest.raises(TypeError, match="BasePluginLoader"):
        PluginDiscovery(loaders=[invalid_loader])
    with pytest.raises(TypeError, match="integer"):
        PluginDiscovery(max_candidates=True)
    with pytest.raises(ValueError, match="at least 1"):
        PluginDiscovery(max_candidates=0)

    discovery = PluginDiscovery()

    assert discovery.loaders == ()
    assert discovery.max_candidates == PluginDiscovery.DEFAULT_MAX_CANDIDATES


def test_plugin_discovery_is_deterministic_for_loaders_and_candidates() -> None:
    candidates_a = (
        _candidate("charlie", "plugins.charlie", source="alpha"),
        _candidate("alpha", "plugins.alpha", source="alpha"),
    )
    candidate_z = _candidate("zulu", "plugins.zulu", source="zulu")

    first_registry = ParserRegistry()
    first = PluginDiscovery(
        loaders=[
            StubLoader((candidate_z,), source_name="zulu"),
            StubLoader(candidates_a, source_name="alpha"),
        ]
    ).discover_and_register(first_registry)

    second_registry = ParserRegistry()
    second = PluginDiscovery(
        loaders=[
            StubLoader(tuple(reversed(candidates_a)), source_name="alpha"),
            StubLoader((candidate_z,), source_name="zulu"),
        ]
    ).discover_and_register(second_registry)

    assert [item.candidate.module_name for item in first.results] == [
        "plugins.alpha",
        "plugins.charlie",
        "plugins.zulu",
    ]
    assert [item.candidate.module_name for item in second.results] == [
        "plugins.alpha",
        "plugins.charlie",
        "plugins.zulu",
    ]
    assert [parser.name for parser in first_registry.list_parsers()] == [
        "alpha",
        "charlie",
        "zulu",
    ]
    assert [parser.name for parser in second_registry.list_parsers()] == [
        "alpha",
        "charlie",
        "zulu",
    ]


def test_candidate_limit_failure_does_not_stop_other_loaders() -> None:
    overflow_loader = StubLoader(
        (
            _candidate("one", "plugins.one", source="alpha"),
            _candidate("two", "plugins.two", source="alpha"),
        ),
        source_name="alpha",
    )
    healthy_loader = StubLoader(
        (_candidate("healthy", "plugins.healthy", source="beta"),),
        source_name="beta",
    )
    registry = ParserRegistry()

    result = PluginDiscovery(
        loaders=[overflow_loader, healthy_loader],
        max_candidates=1,
    ).discover_and_register(registry)

    assert result.loaded_count == 1
    assert result.failed_count == 1
    assert overflow_loader.load_calls == []
    assert registry.contains("healthy")
    assert result.results[0].error_type == PluginDiscoveryError.__name__


def test_loader_discovery_failure_does_not_stop_other_loaders() -> None:
    failing_loader = StubLoader(
        (),
        source_name="alpha",
        discover_error=RuntimeError("secret discovery detail"),
    )
    healthy_loader = StubLoader(
        (_candidate("healthy", "plugins.healthy", source="beta"),),
        source_name="beta",
    )
    registry = ParserRegistry()

    result = PluginDiscovery(
        loaders=[healthy_loader, failing_loader]
    ).discover_and_register(registry)

    assert result.loaded_count == 1
    assert result.failed_count == 1
    assert registry.contains("healthy")
    assert "secret discovery detail" not in (
        result.results[0].error_message or ""
    )


def test_candidate_load_failure_does_not_stop_sibling_candidates() -> None:
    candidates = (
        _candidate("good_two", "plugins.03_good"),
        _candidate("bad", "plugins.02_bad"),
        _candidate("good_one", "plugins.01_good"),
    )
    loader = StubLoader(
        candidates,
        load_error_modules=frozenset({"plugins.02_bad"}),
    )
    registry = ParserRegistry()

    result = PluginDiscovery(loaders=[loader]).discover_and_register(registry)

    assert result.loaded_count == 2
    assert result.registered_count == 2
    assert result.failed_count == 1
    assert [parser.name for parser in registry.list_parsers()] == [
        "good_one",
        "good_two",
    ]
    failed = next(item for item in result.results if not item.success)
    assert "secret loader detail" not in (failed.error_message or "")


def test_replace_flag_does_not_report_new_registration_as_replacement() -> None:
    candidate = _candidate("json", "plugins.json")
    registry = ParserRegistry()

    result = PluginDiscovery(
        loaders=[StubLoader((candidate,))]
    ).discover_and_register(registry, replace=True)

    assert result.registered_count == 1
    assert result.replaced_count == 0
    registration = registry.get_registration("json")
    assert registration.origin == "plugin:stub"


def test_replace_reports_only_an_existing_registry_entry() -> None:
    candidate = _candidate("json", "plugins.json")
    registry = ParserRegistry([FakeParser("json", version="1.0.0")])
    original_order = registry.get_registration("json").registration_order
    loader = StubLoader(
        (candidate,),
        versions={"plugins.json": "2.0.0"},
    )

    result = PluginDiscovery(loaders=[loader]).discover_and_register(
        registry,
        replace=True,
    )

    assert result.replaced_count == 1
    assert registry.get("json").version == "2.0.0"
    registration = registry.get_registration("json")
    assert registration.registration_order == original_order
    assert registration.origin == "plugin:stub"


def test_duplicate_rejection_does_not_stop_following_candidate() -> None:
    registry = ParserRegistry([FakeParser("json")])
    loader = StubLoader(
        (
            _candidate("yaml", "plugins.02_yaml"),
            _candidate("json", "plugins.01_json"),
        )
    )

    result = PluginDiscovery(loaders=[loader]).discover_and_register(registry)

    assert result.failed_count == 1
    assert result.registered_count == 1
    assert registry.contains("json")
    assert registry.contains("yaml")
    failed = next(item for item in result.results if not item.success)
    assert failed.error_type == ParserAlreadyRegisteredError.__name__
