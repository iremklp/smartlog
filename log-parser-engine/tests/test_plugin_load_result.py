from __future__ import annotations

import pytest

from log_parser_engine.exceptions import PluginFactoryError
from log_parser_engine.models import PluginCandidate, PluginLoadResult


def test_loaded_result_requires_parser_details() -> None:
    candidate = PluginCandidate(
        name="json",
        source="package",
        module_name="sample.module",
        origin="package:sample.module",
    )

    result = PluginLoadResult.loaded(
        candidate=candidate,
        parser_name="json",
        parser_version="1.0.0",
        registered=True,
        duration_ms=10.5,
    )

    assert result.success is True
    assert result.parser_name == "json"
    assert result.identifier == "json@1.0.0"


def test_failed_result_requires_error_info() -> None:
    candidate = PluginCandidate(
        name="json",
        source="package",
        module_name="sample.module",
        origin="package:sample.module",
    )

    result = PluginLoadResult.failed(
        candidate=candidate,
        error_type=PluginFactoryError.__name__,
        error_message="factory failed",
        duration_ms=1.5,
    )

    assert result.success is False
    assert result.registered is False
    assert result.error_type == PluginFactoryError.__name__


def test_loaded_result_rejects_invalid_state() -> None:
    candidate = PluginCandidate(
        name="json",
        source="package",
        module_name="sample.module",
        origin="package:sample.module",
    )

    with pytest.raises(ValueError):
        PluginLoadResult(
            candidate=candidate,
            success=True,
            parser_name=None,
            parser_version=None,
            registered=True,
            replaced_existing=False,
            duration_ms=0.0,
        )
