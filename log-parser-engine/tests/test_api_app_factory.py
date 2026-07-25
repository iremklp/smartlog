from __future__ import annotations

from fastapi.testclient import TestClient

from log_parser_engine.api import create_app
from log_parser_engine.application import ApplicationContainer, ApplicationOptions
from log_parser_engine.core import ParserRegistry
from log_parser_engine.models import LogSourceType
from log_parser_engine.storage import InMemoryEventStore
from tests.helpers.fake_parser import FakeParser


def test_api_app_factory_exposes_health_and_request_id() -> None:
    parser = FakeParser(
        "fake",
        source_type=LogSourceType.FILE,
        matched=True,
        confidence=0.9,
        reason="match",
    )
    container = ApplicationContainer.build(
        options=ApplicationOptions(enable_builtin_parsers=False),
        registry=ParserRegistry([parser]),
        store=InMemoryEventStore(),
    )
    app = create_app(container=container)

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["x-request-id"]
    assert response.json()["status"] in {"healthy", "degraded"}


def test_api_parse_endpoint_uses_injected_service() -> None:
    parser = FakeParser(
        "fake",
        source_type=LogSourceType.FILE,
        matched=True,
        confidence=0.9,
        reason="match",
    )
    container = ApplicationContainer.build(
        options=ApplicationOptions(enable_builtin_parsers=False),
        registry=ParserRegistry([parser]),
        store=InMemoryEventStore(),
    )
    app = create_app(container=container)

    client = TestClient(app)
    response = client.post("/parse", json={"raw_log": "hello world"})

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_api_parse_file_and_store_statistics_endpoints() -> None:
    parser = FakeParser(
        "fake",
        source_type=LogSourceType.FILE,
        matched=True,
        confidence=0.9,
        reason="match",
    )
    container = ApplicationContainer.build(
        options=ApplicationOptions(enable_builtin_parsers=False),
        registry=ParserRegistry([parser]),
        store=InMemoryEventStore(),
    )
    app = create_app(container=container)

    client = TestClient(app)
    parse_response = client.post(
        "/parse/file",
        files={"file": ("sample.log", b"hello world", "text/plain")},
    )
    assert parse_response.status_code == 200
    payload = parse_response.json()
    assert payload["success"] is True

    stats_response = client.get("/store/statistics")
    assert stats_response.status_code == 200
    stats = stats_response.json()
    assert "event_count" in stats


def test_api_includes_cors_headers_for_dev_origin() -> None:
    parser = FakeParser(
        "fake",
        source_type=LogSourceType.FILE,
        matched=True,
        confidence=0.9,
        reason="match",
    )
    container = ApplicationContainer.build(
        options=ApplicationOptions(enable_builtin_parsers=False),
        registry=ParserRegistry([parser]),
        store=InMemoryEventStore(),
    )
    app = create_app(container=container)
    client = TestClient(app)

    response = client.options(
        "/health",
        headers={
            "origin": "http://localhost:5173",
            "access-control-request-method": "GET",
        },
    )

    assert response.status_code in {200, 204}
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"