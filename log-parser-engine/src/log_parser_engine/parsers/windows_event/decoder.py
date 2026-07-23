from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from defusedxml import ElementTree as ET  # type: ignore[import-untyped]

from log_parser_engine.exceptions import (
    WindowsEventStructureError,
    WindowsEventXmlError,
)


def decode_windows_event_xml(raw_xml: str) -> ET.Element:
    try:
        root = ET.fromstring(raw_xml)
    except ET.ParseError as exc:
        raise WindowsEventXmlError("invalid Windows Event XML") from exc
    except Exception as exc:  # noqa: BLE001
        raise WindowsEventXmlError("unable to decode Windows Event XML") from exc

    tag = _strip_namespace(root.tag)
    if tag != "Event":
        raise WindowsEventStructureError("root element must be Event")
    return root


def extract_element_text(element: Any) -> str | None:
    if element is None:
        return None
    text = getattr(element, "text", None)
    if text is None:
        return None
    cleaned = text.strip()
    return cleaned or None


def parse_windows_timestamp(value: str) -> datetime:
    cleaned = value.strip()
    if not cleaned:
        raise WindowsEventXmlError("missing event timestamp")
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    try:
        timestamp = datetime.fromisoformat(cleaned)
    except ValueError as exc:
        raise WindowsEventXmlError("invalid event timestamp") from exc
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def _strip_namespace(tag: str) -> str:
    if tag.startswith("{") and "}" in tag:
        return tag.split("}", 1)[1]
    return tag
