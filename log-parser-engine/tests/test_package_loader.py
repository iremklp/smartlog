from __future__ import annotations

import importlib
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest

from log_parser_engine.exceptions import (
    InvalidPluginError,
    PluginDiscoveryError,
    PluginLoadError,
)
from log_parser_engine.models import PluginCandidate
from log_parser_engine.plugins.package_loader import PackagePluginLoader


@pytest.fixture
def package_module(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[ModuleType]:
    package_dir = tmp_path / "demo_plugins"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (package_dir / "json_parser.py").write_text(
        "from log_parser_engine.core import BaseParser\n"
        "from log_parser_engine.models import ParseResult, ParserMetadata\n"
        "from log_parser_engine.core import ParserContext\n"
        "from log_parser_engine.models import DetectionResult\n"
        "class JsonParser(BaseParser):\n"
        "    def __init__(self):\n"
        "        super().__init__()\n"
        "        self._metadata = ParserMetadata(\n"
        "            name='json', display_name='Json', version='1.0.0',\n"
        "            source_type='application'\n"
        "        )\n"
        "    @property\n"
        "    def metadata(self):\n"
        "        return self._metadata\n"
        "    def detect(self, raw_log, context=None):\n"
        "        return DetectionResult.no_match(self.name)\n"
        "    def parse(self, raw_log, context=None):\n"
        "        return ParseResult(status='success')\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()
    module = importlib.import_module("demo_plugins")
    yield module
    for module_name in tuple(sys.modules):
        if module_name == "demo_plugins" or module_name.startswith("demo_plugins."):
            sys.modules.pop(module_name, None)


def test_package_loader_discovers_candidates(package_module: ModuleType) -> None:
    loader = PackagePluginLoader("demo_plugins")

    candidates = loader.discover()

    assert len(candidates) == 1
    assert candidates[0].module_name == "demo_plugins.json_parser"


def test_package_loader_loads_candidate(package_module: ModuleType) -> None:
    loader = PackagePluginLoader("demo_plugins")
    candidate = loader.discover()[0]

    loaded = loader.load(candidate)

    assert loaded is not None


def test_package_loader_rejects_invalid_package() -> None:
    loader = PackagePluginLoader("demo_plugins_missing")

    with pytest.raises(PluginDiscoveryError):
        loader.discover()


def test_package_loader_rejects_invalid_candidate_source() -> None:
    candidate = PluginCandidate(
        name="json",
        source="entry_point",
        module_name="demo_plugins.json_parser",
        origin="entry_point:demo_plugins",
    )
    loader = PackagePluginLoader("demo_plugins")

    with pytest.raises(PluginLoadError):
        loader.load(candidate)


def test_package_loader_requires_manifest_when_configured(
    package_module: ModuleType,
) -> None:
    loader = PackagePluginLoader("demo_plugins", require_manifest=True)

    with pytest.raises(PluginDiscoveryError, match="manifest is required"):
        loader.discover()


def test_package_loader_uses_manifest_as_an_explicit_allowlist(
    package_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package_dir = Path(package_module.__path__[0])
    (package_dir / "helper.py").write_text(
        "class Helper:\n"
        "    pass\n",
        encoding="utf-8",
    )
    importlib.invalidate_caches()
    monkeypatch.setattr(
        package_module,
        "__plugin_modules__",
        ("json_parser",),
        raising=False,
    )
    loader = PackagePluginLoader("demo_plugins", require_manifest=True)

    candidates = loader.discover()

    assert [candidate.module_name for candidate in candidates] == [
        "demo_plugins.json_parser"
    ]


def test_package_loader_treats_empty_manifest_as_empty_allowlist(
    package_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(package_module, "__plugin_modules__", (), raising=False)

    candidates = PackagePluginLoader(
        "demo_plugins",
        require_manifest=True,
    ).discover()

    assert candidates == ()


def test_package_loader_recursive_flag_controls_nested_discovery(
    package_module: ModuleType,
) -> None:
    package_dir = Path(package_module.__path__[0])
    nested_dir = package_dir / "nested"
    nested_dir.mkdir()
    (nested_dir / "__init__.py").write_text("", encoding="utf-8")
    (nested_dir / "nested_parser.py").write_text(
        "from demo_plugins.json_parser import JsonParser\n"
        "Parser = JsonParser\n",
        encoding="utf-8",
    )
    importlib.invalidate_caches()

    shallow_modules = {
        candidate.module_name
        for candidate in PackagePluginLoader(
            "demo_plugins",
            recursive=False,
        ).discover()
    }
    recursive_modules = {
        candidate.module_name
        for candidate in PackagePluginLoader(
            "demo_plugins",
            recursive=True,
        ).discover()
    }

    assert "demo_plugins.nested.nested_parser" not in shallow_modules
    assert "demo_plugins.nested.nested_parser" in recursive_modules


def test_package_loader_does_not_instantiate_non_parser_class_fallback(
    package_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package_dir = Path(package_module.__path__[0])
    (package_dir / "invalid_plugin.py").write_text(
        "constructed = False\n"
        "class Helper:\n"
        "    def __init__(self):\n"
        "        global constructed\n"
        "        constructed = True\n",
        encoding="utf-8",
    )
    importlib.invalidate_caches()
    monkeypatch.setattr(
        package_module,
        "__plugin_modules__",
        ("invalid_plugin",),
        raising=False,
    )
    loader = PackagePluginLoader("demo_plugins", require_manifest=True)
    candidate = loader.discover()[0]

    with pytest.raises(InvalidPluginError, match="no plugin object found"):
        loader.load(candidate)

    invalid_module = importlib.import_module("demo_plugins.invalid_plugin")
    assert invalid_module.constructed is False


def test_package_loader_rejects_candidate_outside_package_namespace() -> None:
    candidate = PluginCandidate(
        name="outside",
        source="package",
        module_name="outside_plugins.parser",
        origin="package:outside_plugins.parser",
    )
    loader = PackagePluginLoader("demo_plugins")

    with pytest.raises(PluginLoadError, match="outside the configured package"):
        loader.load(candidate)


def test_package_loader_rejects_candidate_not_allowed_by_manifest(
    package_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        package_module,
        "__plugin_modules__",
        ("json_parser",),
        raising=False,
    )
    candidate = PluginCandidate(
        name="helper",
        source="package",
        module_name="demo_plugins.helper",
        origin="package:demo_plugins.helper",
    )
    loader = PackagePluginLoader("demo_plugins", require_manifest=True)

    with pytest.raises(PluginLoadError, match="not allowed by the manifest"):
        loader.load(candidate)
