from __future__ import annotations

from contextvars import ContextVar
from uuid import uuid4

request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    return request_id_context.get()


def new_request_id() -> str:
    return uuid4().hex