from __future__ import annotations

from collections.abc import Mapping

import pytest

from log_parser_engine.application import ApplicationContainer, ApplicationOptions
from log_parser_engine.core import ParserRegistry
from log_parser_engine.exceptions import PluginStartupError
from log_parser_engine.models import PluginCandidate
from log_parser_engine.plugins import BasePluginLoader, PluginStartupOptions
from log_parser_engine.storage import InMemoryEventStore
from tests.helpers.fake_parser import FakeParser


def _candidate(name: str, module_name: str) -> PluginCandidate:
    return PluginCandidate(
        name=name,
        source="injected",
        module_name=module_name,
        origin=f"injected:{name}",
    )


class RecordingLoader(BasePluginLoader):
    def __init__(
        self,
        candidates: tuple[PluginCandidate, ...],
        *,
        versions: Mapping[str, str] | None = None,
        failing_modules: frozenset[str] = frozenset(),
    ) -> None:
        self._candidates = candidates
        self._versions = dict(versions or {})
        self._failing_modules = failing_modules
        self.discover_calls = 0
        self.load_calls: list[str] = []
        self.created_parsers: list[FakeParser] = []

    @property
    def source_name(self) -> str:
        return "injected"

    def discover(self) -> tuple[PluginCandidate, ...]:
        self.discover_calls += 1
        return self._candidates

    def load(self, candidate: PluginCandidate) -> object:
        self.load_calls.append(candidate.module_name)
        if candidate.module_name in self._failing_modules:
            raise RuntimeError("secret=/Users/example/private-token")
        parser = FakeParser(
            candidate.name,
            version=self._versions.get(candidate.module_name, "1.0.0"),
        )
        self.created_parsers.append(parser)
        return parser


def _options(
    *,
    failure_policy: str = "fail",
    duplicate_policy: str = "reject",
    enable_builtin_parsers: bool = False,
    allow_builtin_replacement: bool = False,
    max_startup_warnings: int = 20,
    max_warning_length: int = 256,
) -> ApplicationOptions:
    return ApplicationOptions(
        enable_builtin_parsers=enable_builtin_parsers,
        plugin_startup_options=PluginStartupOptions(
            allow_injected_loaders=True,
            failure_policy=failure_policy,
            duplicate_policy=duplicate_policy,
            allow_builtin_replacement=allow_builtin_replacement,
            max_startup_warnings=max_startup_warnings,
            max_warning_length=max_warning_length,
        ),
    )


def test_default_startup_keeps_exact_builtin_order_and_skips_plugins() -> None:
    container = ApplicationContainer()

    assert [parser.name for parser in container.registry.list_parsers()] == [
        "iis_w3c",
        "json_log",
        "redis_log",
        "rfc3164_syslog",
        "rfc5424_syslog",
        "apache_nginx_access",
        "apache_nginx_error",
        "windows_event_xml",
    ]
    assert {
        registration.origin
        for registration in container.registry.list_registrations()
    } == {"builtin"}
    assert container.plugin_discovery_result.discovered_count == 0
    assert container.startup_warnings == ()


def test_injected_loader_requires_explicit_opt_in() -> None:
    loader = RecordingLoader((_candidate("custom", "plugins.custom"),))

    with pytest.raises(PluginStartupError, match="explicit startup opt-in"):
        ApplicationContainer(
            options=ApplicationOptions(enable_builtin_parsers=False),
            plugin_loaders=(loader,),
        )

    assert loader.discover_calls == 0


def test_warn_policy_keeps_good_plugins_and_redacts_bounded_warnings() -> None:
    candidates = (
        _candidate("bad", "plugins.01_bad"),
        _candidate("good", "plugins.02_good"),
    )
    loader = RecordingLoader(
        candidates,
        failing_modules=frozenset({"plugins.01_bad"}),
    )
    container = ApplicationContainer(
        options=_options(
            failure_policy="warn",
            max_startup_warnings=2,
            max_warning_length=80,
        ),
        plugin_loaders=(loader,),
    )

    assert container.registry.contains("good")
    assert not container.registry.contains("bad")
    assert container.plugin_discovery_result.loaded_count == 1
    assert container.plugin_discovery_result.failed_count == 1
    assert container.registry.get_registration("good").origin == "plugin:injected"
    assert len(container.startup_warnings) == 1
    assert len(container.startup_warnings[0]) <= 80
    assert "private-token" not in container.startup_warnings[0]
    assert "/Users/" not in container.startup_warnings[0]


def test_fail_policy_leaves_injected_registry_unchanged() -> None:
    existing = FakeParser("existing")
    registry = ParserRegistry([existing])
    loader = RecordingLoader(
        (
            _candidate("bad", "plugins.01_bad"),
            _candidate("good", "plugins.02_good"),
        ),
        failing_modules=frozenset({"plugins.01_bad"}),
    )

    with pytest.raises(PluginStartupError) as captured:
        ApplicationContainer(
            options=_options(failure_policy="fail"),
            registry=registry,
            store=InMemoryEventStore(),
            plugin_loaders=(loader,),
        )

    assert captured.value.result is not None
    assert captured.value.result.failed_count == 1
    assert [parser.name for parser in registry.list_parsers()] == ["existing"]


def test_duplicate_reject_preserves_original_and_registers_sibling(
) -> None:
    original = FakeParser("duplicate", version="1.0.0")
    registry = ParserRegistry([original])
    loader = RecordingLoader(
        (
            _candidate("duplicate", "plugins.01_duplicate"),
            _candidate("sibling", "plugins.02_sibling"),
        ),
        versions={"plugins.01_duplicate": "2.0.0"},
    )
    container = ApplicationContainer(
        options=_options(failure_policy="warn"),
        registry=registry,
        plugin_loaders=(loader,),
    )

    assert registry.get("duplicate") is original
    assert registry.get("duplicate").version == "1.0.0"
    assert registry.contains("sibling")
    assert container.plugin_discovery_result.failed_count == 1
    assert container.plugin_discovery_result.registered_count == 1


def test_duplicate_replace_preserves_registration_order_and_reports_replacement(
) -> None:
    registry = ParserRegistry([FakeParser("duplicate", version="1.0.0")])
    original_order = registry.get_registration("duplicate").registration_order
    loader = RecordingLoader(
        (_candidate("duplicate", "plugins.duplicate"),),
        versions={"plugins.duplicate": "2.0.0"},
    )
    container = ApplicationContainer(
        options=_options(duplicate_policy="replace"),
        registry=registry,
        plugin_loaders=(loader,),
    )

    registration = registry.get_registration("duplicate")
    assert registry.get("duplicate").version == "2.0.0"
    assert registration.registration_order == original_order
    assert registration.origin == "plugin:injected"
    assert container.plugin_discovery_result.replaced_count == 1


def test_builtin_replacement_is_denied_unless_separately_enabled() -> None:
    loader = RecordingLoader(
        (_candidate("json_log", "plugins.json"),),
        versions={"plugins.json": "9.0.0"},
    )
    container = ApplicationContainer(
        options=_options(
            failure_policy="warn",
            duplicate_policy="replace",
            enable_builtin_parsers=True,
        ),
        plugin_loaders=(loader,),
    )

    assert container.registry.get("json_log").version != "9.0.0"
    assert container.plugin_discovery_result.failed_count == 1
    assert container.registry.get_registration("json_log").origin == "builtin"


def test_lifecycle_runs_once_and_returns_its_cached_outcome() -> None:
    loader = RecordingLoader((_candidate("custom", "plugins.custom"),))
    container = ApplicationContainer(
        options=_options(),
        plugin_loaders=(loader,),
    )

    repeated = container.plugin_startup_lifecycle.run(container.registry)

    assert loader.discover_calls == 1
    assert repeated.discovery_result is container.plugin_discovery_result


def test_empty_injected_registry_is_preserved() -> None:
    registry = ParserRegistry()
    container = ApplicationContainer(
        options=ApplicationOptions(enable_builtin_parsers=True),
        registry=registry,
    )

    assert container.registry is registry
    assert container.registry.count == 0
