from __future__ import annotations

from log_parser_engine.models import (
    PluginCandidate,
    PluginDiscoveryResult,
    PluginLoadResult,
)


def test_discovery_result_counts_and_identifiers() -> None:
    candidate = PluginCandidate(
        name="json",
        source="package",
        module_name="sample.module",
        origin="package:sample.module",
    )
    success = PluginLoadResult.loaded(
        candidate=candidate,
        parser_name="json",
        parser_version="1.0.0",
        registered=True,
        duration_ms=2.0,
    )
    failed = PluginLoadResult.failed(
        candidate=candidate,
        error_type="PluginFactoryError",
        error_message="factory failed",
        duration_ms=1.0,
    )

    result = PluginDiscoveryResult(results=(success, failed))

    assert result.discovered_count == 2
    assert result.loaded_count == 1
    assert result.failed_count == 1
    assert result.registered_count == 1
    assert result.all_successful is False
    assert result.has_failures is True
    assert result.loaded_identifiers == ("json@1.0.0",)
