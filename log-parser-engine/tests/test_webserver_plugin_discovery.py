from __future__ import annotations

from log_parser_engine.core import ParserRegistry
from log_parser_engine.parsers import (
    ApacheNginxAccessLogParser,
    ApacheNginxErrorLogParser,
)
from log_parser_engine.plugins.package_loader import PackagePluginLoader
from log_parser_engine.plugins.plugin_discovery import PluginDiscovery


def test_webserver_public_imports_expose_parser_classes() -> None:
    assert ApacheNginxAccessLogParser.__name__ == "ApacheNginxAccessLogParser"
    assert ApacheNginxErrorLogParser.__name__ == "ApacheNginxErrorLogParser"


def test_webserver_package_loader_discovers_only_entry_modules() -> None:
    loader = PackagePluginLoader("log_parser_engine.parsers.webserver")

    candidates = loader.discover()
    module_names = [candidate.module_name for candidate in candidates]

    assert module_names == [
        "log_parser_engine.parsers.webserver.access_plugin",
        "log_parser_engine.parsers.webserver.error_plugin",
    ]


def test_webserver_plugin_modules_expose_only_parser_alias() -> None:
    from log_parser_engine.parsers.webserver import access_plugin, error_plugin

    assert access_plugin.Parser is ApacheNginxAccessLogParser
    assert error_plugin.Parser is ApacheNginxErrorLogParser
    assert not hasattr(access_plugin, "create_parser")
    assert not hasattr(error_plugin, "create_parser")


def test_webserver_plugin_discovery_registers_two_parsers() -> None:
    loader = PackagePluginLoader("log_parser_engine.parsers.webserver")
    registry = ParserRegistry()

    result = PluginDiscovery(loaders=[loader]).discover_and_register(registry=registry)

    assert result.discovered_count == 2
    assert result.loaded_count == 2
    assert result.registered_count == 2
    assert result.failed_count == 0
    assert [item.name for item in registry.list_parsers()] == [
        "apache_nginx_access",
        "apache_nginx_error",
    ]


def test_webserver_helper_modules_are_not_plugin_candidates() -> None:
    loader = PackagePluginLoader("log_parser_engine.parsers.webserver")
    candidate_modules = {candidate.module_name for candidate in loader.discover()}

    for helper_module in (
        "log_parser_engine.parsers.webserver.constants",
        "log_parser_engine.parsers.webserver.helpers",
        "log_parser_engine.parsers.webserver.access_parser",
        "log_parser_engine.parsers.webserver.error_parser",
    ):
        assert helper_module not in candidate_modules


def test_webserver_discovery_is_deterministic() -> None:
    loader = PackagePluginLoader("log_parser_engine.parsers.webserver")

    first = [candidate.module_name for candidate in loader.discover()]
    second = [candidate.module_name for candidate in loader.discover()]

    assert first == second