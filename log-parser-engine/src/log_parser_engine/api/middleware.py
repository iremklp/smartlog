from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .request_id import (
    get_request_id,
    new_request_id,
    request_id_context,
    resolve_request_id,
)
from .schemas import AnalysisApiErrorDetail, AnalysisApiErrorResponse

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
        response_model = AnalysisApiErrorResponse(
            detail="Analysis request body exceeds limit.",
            error=AnalysisApiErrorDetail(
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
    request.state.request_id = request_id
    token = request_id_context.set(request_id)
    try:
        response = await call_next(request)
    finally:
        request_id_context.reset(token)
    response.headers["X-Request-ID"] = request_id
    for name, value in _SECURITY_HEADERS.items():
        response.headers[name] = value
    return response
