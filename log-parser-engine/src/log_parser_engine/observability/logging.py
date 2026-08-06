from __future__ import annotations

import json
import logging
import os
import sys
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from .context import get_operation_id, get_request_id

_SENSITIVE_KEY_PARTS = (
    "raw",
    "bytes",
    "metadata",
    "message",
    "upload",
    "attribute",
    "search",
    "token",
    "credential",
    "password",
    "authorization",
)

_CONFIGURED = False


class JsonLogFormatter(logging.Formatter):
    """Format records as one-line JSON objects for log collectors."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
        }
        message = record.msg
        if isinstance(message, Mapping):
            payload.update(message)
        else:
            payload["message"] = record.getMessage()
        if record.exc_info and record.exc_info[0] is not None:
            payload["error_type"] = record.exc_info[0].__name__
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_structured_logging(*, force: bool = False) -> None:
    global _CONFIGURED
    if _CONFIGURED and not force:
        return

    format_name = os.getenv("LOG_PARSER_LOG_FORMAT", "json").strip().lower()
    level_name = os.getenv("LOG_PARSER_LOG_LEVEL", "INFO").strip().upper()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    if format_name == "plain":
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
    else:
        handler.setFormatter(JsonLogFormatter())

    logger = logging.getLogger("log_parser_engine")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False

    disable_uvicorn_access = _parse_bool_env(
        "LOG_PARSER_DISABLE_UVICORN_ACCESS_LOG",
        default=True,
    )
    logging.getLogger("uvicorn.access").disabled = disable_uvicorn_access

    _CONFIGURED = True


def emit_structured_log(
    logger: logging.Logger,
    *,
    event: str,
    level: int = logging.INFO,
    **fields: Any,
) -> None:
    payload: dict[str, object] = {
        "event": event,
        "request_id": get_request_id(),
        "operation_id": get_operation_id(),
    }
    payload.update(_sanitize_fields(fields))
    logger.log(level, payload)


def emit_structured_log_fields(
    logger: logging.Logger,
    *,
    event: str,
    fields: Mapping[str, Any],
    level: int = logging.INFO,
) -> None:
    payload: dict[str, object] = {
        "event": event,
        "request_id": get_request_id(),
        "operation_id": get_operation_id(),
    }
    payload.update(_sanitize_fields(fields))
    logger.log(level, payload)


def _sanitize_fields(fields: Mapping[str, Any]) -> dict[str, object]:
    safe: dict[str, object] = {}
    for key, value in fields.items():
        if value is None:
            continue
        if _is_sensitive_key(key):
            safe[key] = "[REDACTED]"
            continue
        if isinstance(value, (bool, int, float)):
            safe[key] = value
            continue
        if isinstance(value, str):
            safe[key] = value[:256]
            continue
        if isinstance(value, (tuple, list, set)):
            safe[f"{key}_count"] = len(value)
            continue
        if isinstance(value, Mapping):
            safe[f"{key}_count"] = len(value)
            continue
        safe[key] = str(value)[:128]
    return safe


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in _SENSITIVE_KEY_PARTS)


def _parse_bool_env(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}
