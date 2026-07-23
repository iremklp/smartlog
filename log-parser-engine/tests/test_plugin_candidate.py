from __future__ import annotations

import pytest

from log_parser_engine.models import PluginCandidate


def test_candidate_qualified_name_uses_object_name() -> None:
    candidate = PluginCandidate(
        name="json",
        source="package",
        module_name="log_parser_engine.parsers.json",
        object_name="Parser",
        origin="package:log_parser_engine.parsers.json",
    )

    assert candidate.qualified_name == "log_parser_engine.parsers.json:Parser"


def test_candidate_trims_and_rejects_empty_values() -> None:
    with pytest.raises(ValueError):
        PluginCandidate(
            name="   ",
            source="package",
            module_name="module",
            origin="package:module",
        )

    with pytest.raises(ValueError):
        PluginCandidate(
            name="json",
            source="",
            module_name="module",
            origin="package:module",
        )
