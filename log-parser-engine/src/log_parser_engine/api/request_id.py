from __future__ import annotations

from contextvars import ContextVar
from re import fullmatch
from uuid import uuid4

request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)

_REQUEST_ID_PATTERN = r"[A-Za-z0-9._:-]{1,128}"


def get_request_id() -> str | None:
    return request_id_context.get()


def new_request_id() -> str:
    return uuid4().hex


def resolve_request_id(
    incoming: str | None,
    *,
    trust_incoming: bool,
) -> str:
    """Return a safe request ID without trusting client input by default."""

    if not trust_incoming or incoming is None:
        return new_request_id()
    candidate = incoming.strip()
    if fullmatch(_REQUEST_ID_PATTERN, candidate) is None:
        return new_request_id()
    return candidate
