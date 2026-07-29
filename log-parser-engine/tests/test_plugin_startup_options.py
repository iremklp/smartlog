from __future__ import annotations

import pytest
from pydantic import ValidationError

from log_parser_engine.plugins import PluginStartupOptions


def test_plugin_startup_is_disabled_by_default() -> None:
    options = PluginStartupOptions()

    assert options.enabled is False
    assert options.package_names == ()
    assert options.enable_entry_points is False
    assert options.duplicate_policy == "reject"
    assert options.failure_policy == "fail"


def test_plugin_startup_normalizes_and_deduplicates_sources() -> None:
    options = PluginStartupOptions(
        package_names=(" company.parsers ", "company.parsers"),
        enable_entry_points=True,
        entry_point_names=("iis", " iis ", "custom-json"),
    )

    assert options.enabled is True
    assert options.package_names == ("company.parsers",)
    assert options.entry_point_names == ("iis", "custom-json")


def test_entry_point_discovery_requires_an_explicit_name_allowlist() -> None:
    with pytest.raises(ValidationError, match="entry_point_names"):
        PluginStartupOptions(enable_entry_points=True)


@pytest.mark.parametrize(
    "package_name",
    (
        "../plugins",
        "company..plugins",
        "company._private",
        "company.plugins-with-dash",
    ),
)
def test_package_names_reject_unsafe_module_paths(package_name: str) -> None:
    with pytest.raises(ValidationError, match="invalid dotted name"):
        PluginStartupOptions(package_names=(package_name,))


def test_plugin_startup_options_are_immutable() -> None:
    options = PluginStartupOptions()

    with pytest.raises(ValidationError):
        options.failure_policy = "warn"  # type: ignore[misc]
