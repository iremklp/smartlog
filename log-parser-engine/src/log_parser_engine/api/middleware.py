from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from time import perf_counter

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from log_parser_engine.observability.logging import emit_structured_log

from .request_id import (
    get_request_id,
    new_operation_id,
    new_request_id,
    operation_id_context,
    request_id_context,
    resolve_request_id,
)
from .schemas import ApiErrorDetail, ApiErrorResponse

_SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}

_ANALYSIS_PATHS = frozenset(
    {
        "/analysis",
        "/analysis/compare",
        "/api/v1/analysis",
        "/api/v1/analysis/compare",
    }
)

_REQUEST_LOGGER = logging.getLogger("log_parser_engine.request")


class AnalysisRequestSizeLimitMiddleware:
    """Bound analysis request bodies before FastAPI materializes their JSON."""

    def __init__(self, app: ASGIApp, *, max_body_bytes: int) -> None:
        if max_body_bytes <= 0:
            raise ValueError("max_body_bytes must be positive")
        self._app = app
        self._max_body_bytes = max_body_bytes

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if (
            scope["type"] != "http"
            or scope.get("method") != "POST"
            or scope.get("path") not in _ANALYSIS_PATHS
        ):
            await self._app(scope, receive, send)
            return

        content_length = self._content_length(scope)
        if (
            content_length is not None
            and content_length > self._max_body_bytes
        ):
            await self._reject(scope, receive, send)
            return

        received_bytes = 0
        buffered_messages: list[Message] = []
        while True:
            message = await receive()
            buffered_messages.append(message)
            if message["type"] == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > self._max_body_bytes:
                    await self._reject(scope, receive, send)
                    return
                if not message.get("more_body", False):
                    break
            elif message["type"] == "http.disconnect":
                break

        message_index = 0

        async def receive_buffered() -> Message:
            nonlocal message_index
            if message_index < len(buffered_messages):
                message = buffered_messages[message_index]
                message_index += 1
                return message
            return await receive()

        await self._app(scope, receive_buffered, send)

    @staticmethod
    def _content_length(scope: Scope) -> int | None:
        for name, raw_value in scope.get("headers", ()):
            if name.lower() != b"content-length":
                continue
            try:
                value = int(raw_value)
            except ValueError:
                return None
            return value if value >= 0 else None
        return None

    async def _reject(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        request_id = get_request_id() or new_request_id()
        response_model = ApiErrorResponse(
            detail="Analysis request body exceeds limit.",
            error=ApiErrorDetail(
                code="ANALYSIS_REQUEST_BODY_TOO_LARGE",
                message="Analysis request body exceeds limit.",
                request_id=request_id,
                timestamp=datetime.now(timezone.utc),
                details={"limit_bytes": self._max_body_bytes},
            ),
        )
        response = JSONResponse(
            status_code=413,
            content=response_model.model_dump(mode="json"),
        )
        await response(scope, receive, send)


async def request_id_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    incoming = request.headers.get("X-Request-ID")
    options = request.app.state.container.options
    request_id = resolve_request_id(
        incoming,
        trust_incoming=options.trust_incoming_request_id,
    )
    operation_id = new_operation_id()
    route = request.url.path
    method = request.method
    request.state.request_id = request_id
    request.state.operation_id = operation_id
    token = request_id_context.set(request_id)
    operation_token = operation_id_context.set(operation_id)
    started = perf_counter()
    emit_structured_log(
        _REQUEST_LOGGER,
        event="api.request.started",
        method=method,
        route=route,
    )
    try:
        response = await call_next(request)
    except Exception as exc:
        duration_ms = (perf_counter() - started) * 1000.0
        _record_request_metrics(request, duration_ms=duration_ms)
        emit_structured_log(
            _REQUEST_LOGGER,
            event="api.request.failed",
            level=logging.ERROR,
            method=method,
            route=route,
            duration_ms=duration_ms,
            error_type=exc.__class__.__name__,
        )
        raise
    finally:
        operation_id_context.reset(operation_token)
        request_id_context.reset(token)
    duration_ms = (perf_counter() - started) * 1000.0
    is_slow = _record_request_metrics(request, duration_ms=duration_ms)
    emit_structured_log(
        _REQUEST_LOGGER,
        event="api.request.completed",
        method=method,
        route=route,
        status_code=response.status_code,
        duration_ms=duration_ms,
    )
    if is_slow:
        emit_structured_log(
            _REQUEST_LOGGER,
            event="api.request.slow",
            level=logging.WARNING,
            method=method,
            route=route,
            status_code=response.status_code,
            duration_ms=duration_ms,
            slow_threshold_ms=options.slow_request_threshold_ms,
        )
    response.headers["X-Request-ID"] = request_id
    for name, value in _SECURITY_HEADERS.items():
        response.headers[name] = value
    return response


def _record_request_metrics(request: Request, *, duration_ms: float) -> bool:
    options = request.app.state.container.options
    threshold_ms = float(options.slow_request_threshold_ms)
    is_slow = duration_ms >= threshold_ms
    request.app.state.container.request_runtime_metrics.record_request(
        duration_ms=duration_ms,
        slow=is_slow,
    )
    return is_slow
