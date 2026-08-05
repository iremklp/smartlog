from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, cast

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from log_parser_engine.analysis import AnalysisOptions
from log_parser_engine.api import create_app
from log_parser_engine.api.middleware import AnalysisRequestSizeLimitMiddleware
from log_parser_engine.application import ApplicationContainer, ApplicationOptions
from log_parser_engine.core import ParserRegistry
from log_parser_engine.models import LogEvent, LogSeverity, LogSourceType
from log_parser_engine.storage import InMemoryEventStore


def _client(
    *,
    max_events: int = 100,
    analysis_overrides: dict[str, Any] | None = None,
    application_overrides: dict[str, Any] | None = None,
) -> TestClient:
    option_values = {"max_events": max_events, **(analysis_overrides or {})}
    options = ApplicationOptions(
        enable_builtin_parsers=False,
        analysis_options=AnalysisOptions(**option_values),
        **(application_overrides or {}),
    )
    container = ApplicationContainer.build(
        options=options,
        registry=ParserRegistry([]),
        store=InMemoryEventStore(),
    )
    container.store.add(
        LogEvent(
            timestamp=datetime(2026, 7, 25, 10, tzinfo=timezone.utc),
            source_type=LogSourceType.HTTP,
            severity=LogSeverity.ERROR,
            message="safe event",
            raw_message="raw credential should not be returned",
            service="gateway",
            http_method="GET",
            http_path="/api/items",
            http_status=500,
            duration_ms=150,
        )
    )
    return TestClient(create_app(container=container))


def test_analysis_api_returns_safe_statistical_result_and_metrics() -> None:
    client = _client()

    response = client.post(
        "/api/v1/analysis",
        json={
            "filter": {
                "message_contains": "SAFE EVENT",
                "message_case_sensitive": False,
            },
            "include_samples": True,
            "sample_size": 1,
            "metadata": {"private_search_context": "do-not-echo"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["matched_event_count"] == 1
    assert body["summary"]["error_count"] == 1
    assert body["http"]["server_error_count"] == 1
    assert "raw credential" not in response.text
    assert "do-not-echo" not in response.text
    assert "SAFE EVENT" not in response.text
    assert "request" not in body
    assert "metadata" not in body
    assert response.headers["x-request-id"]

    metrics = client.get("/runtime/statistics").json()
    assert metrics["analysis_operations_total"] == 1
    assert metrics["analyzed_events_total"] == 1


def test_analysis_compare_api_supports_versioned_alias() -> None:
    client = _client()

    response = client.post(
        "/api/v1/analysis/compare",
        json={
            "baseline_filter": {
                "end_time": "2026-07-25T10:00:00Z",
            },
            "comparison_filter": {
                "start_time": "2026-07-25T10:00:00Z",
            },
            "metrics": ["event_count", "error_rate"],
            "group_by": ["service"],
            "metadata": {"private_comparison_context": "do-not-echo"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["baseline_event_count"] == 0
    assert body["comparison_event_count"] == 1
    assert "do-not-echo" not in response.text
    assert "metadata" not in body
    metrics = client.get("/runtime/statistics").json()
    assert metrics["comparison_operations_total"] == 1


def test_analysis_event_limit_maps_to_413() -> None:
    client = _client(max_events=1)
    second = {
        "event": {
            "timestamp": "2026-07-25T11:00:00Z",
            "source_type": "APPLICATION",
            "severity": "INFO",
            "message": "second",
            "raw_message": "second",
        }
    }
    assert client.post("/events", json=second).status_code == 200

    response = client.post("/analysis", json={})

    assert response.status_code == 413
    assert "exceeds limit" in response.json()["detail"]
    error = response.json()["error"]
    assert error["code"] == "ANALYSIS_EVENT_LIMIT_EXCEEDED"
    assert error["request_id"] == response.headers["x-request-id"]
    assert error["timestamp"]
    assert error["details"] == {"event_count": 2, "limit": 1}

    metrics = client.get("/runtime/statistics").json()
    assert metrics["analysis_operations_total"] == 1
    assert metrics["analysis_operations_failed"] == 1
    assert metrics["analyzed_events_total"] == 0


def test_analysis_openapi_documents_v1_routes_and_hides_legacy_aliases() -> None:
    client = _client()

    schema = client.get("/openapi.json").json()
    paths = schema["paths"]

    assert "/api/v1/analysis" in paths
    assert "/api/v1/analysis/compare" in paths
    assert "/analysis" not in paths
    assert "/analysis/compare" not in paths
    response_schema = schema["components"]["schemas"]["AnalysisApiResponse"]
    assert "request" not in response_schema["properties"]
    assert "metadata" not in response_schema["properties"]


def test_analysis_legacy_alias_remains_compatible() -> None:
    client = _client()

    response = client.post("/analysis", json={})

    assert response.status_code == 200
    assert response.json()["matched_event_count"] == 1


def test_analysis_validation_error_is_safe_and_traceable() -> None:
    client = _client()

    response = client.post(
        "/api/v1/analysis",
        json={
            "top_n": 0,
            "metadata": {"secret": "must-not-echo"},
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "ANALYSIS_REQUEST_VALIDATION_FAILED"
    assert body["error"]["request_id"] == response.headers["x-request-id"]
    assert body["error"]["timestamp"]
    assert body["error"]["details"]["fields"] == ["top_n"]
    assert "must-not-echo" not in response.text
    assert "input" not in response.text


def test_analysis_api_rejects_unconfigured_attribute_group_fields() -> None:
    client = _client()
    add_response = client.post(
        "/events",
        json={
            "event": {
                "timestamp": "2026-07-25T10:01:00Z",
                "source_type": "APPLICATION",
                "severity": "INFO",
                "message": "private attribute event",
                "raw_message": "private attribute event",
                "attributes": {
                    "customer_email": "person@example.test",
                    "private_key": "must-not-be-returned",
                },
            }
        },
    )
    assert add_response.status_code == 200

    for field in ("customer_email", "private_key"):
        response = client.post(
            "/api/v1/analysis",
            json={"group_fields": [field]},
        )

        assert response.status_code == 422
        assert "person@example.test" not in response.text
        assert "must-not-be-returned" not in response.text


def test_analysis_api_rejects_non_public_group_dimension_paths() -> None:
    client = _client()

    response = client.post(
        "/api/v1/analysis",
        json={"group_fields": ["attributes.team"]},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "ANALYSIS_REQUEST_VALIDATION_FAILED"
    assert body["error"]["details"]["fields"] == ["group_fields"]


def test_analysis_validation_error_fields_are_deduplicated_and_bounded() -> None:
    client = _client()
    payload: dict[str, object] = {"top_n": 0}
    for index in range(30):
        payload[f"unknown_field_{index}"] = index

    response = client.post("/api/v1/analysis", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "ANALYSIS_REQUEST_VALIDATION_FAILED"

    fields = body["error"]["details"]["fields"]
    assert isinstance(fields, list)
    assert len(fields) == 20
    assert len(fields) == len(set(fields))
    assert all(
        isinstance(field, str) and field and "body" not in field
        for field in fields
    )


def test_analysis_api_bounds_request_body_before_json_materialization() -> None:
    client = _client(
        application_overrides={"max_analysis_request_body_bytes": 256}
    )
    oversized_body = (
        '{"metadata":{"value":"' + ("x" * 1_024) + '"}}'
    )

    response = client.post(
        "/api/v1/analysis",
        content=oversized_body,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413
    assert (
        response.json()["error"]["code"]
        == "ANALYSIS_REQUEST_BODY_TOO_LARGE"
    )
    assert response.json()["error"]["details"] == {"limit_bytes": 256}
    assert response.headers["x-request-id"]


def test_analysis_body_limit_handles_chunked_body_without_content_length() -> None:
    async def exercise_middleware() -> tuple[bool, list[Message]]:
        downstream_called = False

        async def downstream(
            scope: Scope,
            receive: Receive,
            send: Send,
        ) -> None:
            nonlocal downstream_called
            downstream_called = True

        middleware = AnalysisRequestSizeLimitMiddleware(
            cast(ASGIApp, downstream),
            max_body_bytes=256,
        )
        incoming = iter(
            (
                {
                    "type": "http.request",
                    "body": b"x" * 200,
                    "more_body": True,
                },
                {
                    "type": "http.request",
                    "body": b"y" * 200,
                    "more_body": False,
                },
            )
        )
        sent: list[Message] = []

        async def receive() -> Message:
            return next(incoming)

        async def send(message: Message) -> None:
            sent.append(message)

        await middleware(
            {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": "POST",
                "scheme": "http",
                "path": "/api/v1/analysis",
                "raw_path": b"/api/v1/analysis",
                "query_string": b"",
                "headers": [],
                "client": ("127.0.0.1", 1234),
                "server": ("testserver", 80),
            },
            receive,
            send,
        )
        return downstream_called, sent

    downstream_called, messages = asyncio.run(exercise_middleware())
    response_start = next(
        message
        for message in messages
        if message["type"] == "http.response.start"
    )
    response_body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )

    assert not downstream_called
    assert response_start["status"] == 413
    assert (
        json.loads(response_body)["error"]["code"]
        == "ANALYSIS_REQUEST_BODY_TOO_LARGE"
    )


def test_analysis_api_rejects_oversized_timeline_bucket_safely() -> None:
    client = _client()

    response = client.post(
        "/api/v1/analysis",
        json={"time_bucket_seconds": 10**20},
    )

    assert response.status_code == 422
    assert (
        response.json()["error"]["code"]
        == "ANALYSIS_REQUEST_VALIDATION_FAILED"
    )
    assert response.headers["x-request-id"]


def test_analysis_api_maps_datetime_boundary_to_safe_timeline_error() -> None:
    client = _client()
    add_response = client.post(
        "/events",
        json={
            "event": {
                "timestamp": "9999-12-31T23:59:00Z",
                "source_type": "HTTP",
                "severity": "INFO",
                "message": "upper datetime boundary",
                "raw_message": "upper datetime boundary",
            }
        },
    )
    assert add_response.status_code == 200

    response = client.post("/api/v1/analysis", json={})

    assert response.status_code == 400
    assert (
        response.json()["error"]["code"]
        == "ANALYSIS_TIMELINE_LIMIT_EXCEEDED"
    )
    assert response.headers["x-request-id"]


def test_analysis_api_rejects_work_when_concurrency_slots_are_full() -> None:
    client = _client(
        application_overrides={"max_concurrent_analysis_operations": 1}
    )
    container = cast(FastAPI, client.app).state.container
    assert container.try_acquire_analysis_slot()
    try:
        response = client.post("/api/v1/analysis", json={})
    finally:
        container.release_analysis_slot()

    assert response.status_code == 429
    assert (
        response.json()["error"]["code"]
        == "ANALYSIS_CONCURRENCY_LIMIT_REACHED"
    )
    assert response.json()["error"]["details"] == {"limit": 1}
    assert response.headers["retry-after"] == "1"
    assert response.headers["x-request-id"]


def test_analysis_enforces_runtime_request_limits() -> None:
    client = _client(
        analysis_overrides={
            "max_top_n": 2,
            "default_top_n": 2,
            "max_samples_per_request": 2,
        }
    )

    top_n_response = client.post("/api/v1/analysis", json={"top_n": 3})
    sample_response = client.post(
        "/api/v1/analysis",
        json={"include_samples": True, "sample_size": 3},
    )

    assert top_n_response.status_code == 400
    assert top_n_response.json()["error"]["code"] == "ANALYSIS_REQUEST_INVALID"
    assert sample_response.status_code == 400
    assert sample_response.json()["error"]["code"] == "ANALYSIS_REQUEST_INVALID"


def test_analysis_enforces_configured_field_and_metric_limits() -> None:
    client = _client(
        analysis_overrides={
            "max_group_fields_per_request": 1,
            "max_percentiles_per_request": 1,
            "max_comparison_metrics_per_request": 1,
        }
    )

    grouped = client.post(
        "/api/v1/analysis",
        json={"group_fields": ["severity", "service"]},
    )
    percentiles = client.post(
        "/api/v1/analysis",
        json={"percentiles": [50, 95]},
    )
    comparison_groups = client.post(
        "/api/v1/analysis/compare",
        json={"metrics": ["event_count"], "group_by": ["severity", "service"]},
    )
    comparison_metrics = client.post(
        "/api/v1/analysis/compare",
        json={
            "metrics": ["event_count", "error_rate"],
            "group_by": ["severity"],
        },
    )

    assert grouped.status_code == 400
    assert percentiles.status_code == 400
    assert comparison_groups.status_code == 400
    assert comparison_metrics.status_code == 400


def test_failed_comparison_records_zero_analyzed_events() -> None:
    client = _client(
        analysis_overrides={
            "max_top_n": 2,
            "default_top_n": 2,
        }
    )

    response = client.post(
        "/api/v1/analysis/compare",
        json={"top_n": 3},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "ANALYSIS_COMPARISON_INVALID"
    metrics = client.get("/runtime/statistics").json()
    assert metrics["comparison_operations_total"] == 1
    assert metrics["comparison_operations_failed"] == 1
    assert metrics["analyzed_events_total"] == 0


def test_analysis_response_bounds_dimensions_and_never_exposes_raw_message() -> None:
    client = _client(
        analysis_overrides={"max_dimension_value_length": 16}
    )
    long_dimension = "service-" + ("x" * 100)
    raw_secret = "raw-secret-" + ("y" * 100)
    add_response = client.post(
        "/events",
        json={
            "event": {
                "timestamp": "2026-07-25T10:01:00Z",
                "source_type": "HTTP",
                "severity": "ERROR",
                "message": "bounded response event",
                "raw_message": raw_secret,
                "service": long_dimension,
                "http_method": "POST",
                "http_path": "/api/" + ("segment" * 50),
                "http_status": 503,
                "duration_ms": 250,
            }
        },
    )
    assert add_response.status_code == 200

    response = client.post(
        "/api/v1/analysis",
        json={"include_samples": True, "sample_size": 2},
    )

    assert response.status_code == 200
    assert raw_secret not in response.text
    assert long_dimension not in response.text
    for distribution in response.json()["distributions"]:
        for item in distribution["items"]:
            assert len(item["key"]) <= 16
