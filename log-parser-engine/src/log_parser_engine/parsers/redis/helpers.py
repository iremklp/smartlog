from __future__ import annotations

import re
from typing import Final

from log_parser_engine.exceptions import RedisMappingError

_ENDPOINT_RE: Final = re.compile(r"^(?:(\[[^\]]+\]|[^:]+))(?:\:(\d{1,5}))?$")


def parse_endpoint(value: str) -> tuple[str | None, int | None]:
    if not value or not value.strip():
        raise RedisMappingError("endpoint must not be empty")
    cleaned = value.strip()
    match = _ENDPOINT_RE.fullmatch(cleaned)
    if not match:
        raise RedisMappingError("invalid endpoint")
    host = match.group(1)
    port_text = match.group(2)
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    port = int(port_text) if port_text is not None else None
    if port is not None and not 1 <= port <= 65535:
        raise RedisMappingError("invalid port")
    return host, port


def safe_summary(message: str, max_length: int = 300) -> str:
    cleaned = " ".join(str(message).split())
    if len(cleaned) <= max_length:
        return cleaned
    return cleaned[: max_length - 3].rstrip() + "..."


def sanitize_event_fragment(value: str) -> str:
    return " ".join(str(value).split())
