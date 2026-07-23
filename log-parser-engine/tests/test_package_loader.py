from __future__ import annotations

import importlib
from pathlib import Path
from types import ModuleType

import pytest

from log_parser_engine.exceptions import PluginDiscoveryError, PluginLoadError
from log_parser_engine.models import PluginCandidate
from log_parser_engine.plugins.package_loader import PackagePluginLoader


@pytest.fixture
def package_module(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
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
    module = importlib.import_module("demo_plugins")
    return module


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
