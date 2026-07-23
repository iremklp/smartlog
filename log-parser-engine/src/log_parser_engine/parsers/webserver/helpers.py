from __future__ import annotations

import re
from typing import Any


def normalize_vendor(value: Any) -> str:
    if value is None:
        return "generic"
    cleaned = str(value).strip().lower()
    return cleaned or "generic"


def normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return str(value)


def parse_status(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        if cleaned.isdigit():
            return int(cleaned)
    return None


def normalize_severity(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip().lower()
        if cleaned in {"error", "warn", "warning", "notice", "info", "debug", "crit", "critical", "emerg", "alert"}:
            return cleaned
    return None


def detect_http_method(request: Any) -> str | None:
    if not isinstance(request, str):
        return None
    match = re.match(r'^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\b', request.upper())
    if match:
        return match.group(1).lower()
    return None
