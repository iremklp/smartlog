from __future__ import annotations

import json
from pathlib import Path

from log_parser_engine.api.main import app


def _schema_snapshot_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "frontend"
        / "src"
        / "lib"
        / "api"
        / "generated"
        / "openapi.schema.json"
    )


def test_openapi_schema_snapshot_is_current() -> None:
    snapshot_path = _schema_snapshot_path()
    expected = json.loads(snapshot_path.read_text(encoding="utf-8"))
    current = app.openapi()

    assert current == expected, (
        "OpenAPI snapshot drift detected. Regenerate frontend contract files with "
        "`cd frontend && npm run contract:generate`."
    )


def test_openapi_contract_field_names_are_stable() -> None:
    schema = app.openapi()
    components = schema["components"]["schemas"]

    parse_request_properties = components["ParseRequest"]["properties"]
    assert "raw_log" in parse_request_properties

    log_event_properties = components["LogEvent"]["properties"]
    assert "raw_message" in log_event_properties
    assert "raw_log" not in log_event_properties

    event_page_properties = components["EventPage"]["properties"]
    assert "offset" in event_page_properties
    assert "limit" in event_page_properties
    assert "returned" in event_page_properties
    assert "total" in event_page_properties
    assert "has_more" not in event_page_properties
    assert "has_next" not in event_page_properties

    paths = schema["paths"]
    assert "/api/v1/analysis" in paths
    assert "/api/v1/analysis/compare" in paths
