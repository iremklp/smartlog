"""Foundation models for deterministic report generation contracts."""

from __future__ import annotations

import json
import math
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .immutable import FrozenDict, freeze_mapping

_SUPPORTED_REPORT_FORMATS = frozenset({"json", "markdown", "html", "csv"})
_SUPPORTED_REPORT_SECTIONS = frozenset(
    {
        "summary",
        "timeline",
        "distributions",
        "latency",
        "http",
        "insights",
        "samples",
        "comparison",
    }
)
_MAX_REPORT_NAME_LENGTH = 120
_MAX_SECTIONS = 16
_MAX_METADATA_DEPTH = 5
_MAX_METADATA_KEYS = 100
_MAX_METADATA_BYTES = 16_384


def _validate_json_value(value: object, *, depth: int = 0) -> None:
    if depth > _MAX_METADATA_DEPTH:
        raise ValueError("metadata nesting is too deep")
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("metadata numeric values must be finite")
        return
    if isinstance(value, list):
        for item in value:
            _validate_json_value(item, depth=depth + 1)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or not key or key.startswith("__"):
                raise ValueError("metadata keys must be safe non-empty strings")
            _validate_json_value(item, depth=depth + 1)
        return
    raise ValueError("metadata must contain JSON-safe values")


def _safe_metadata(value: dict[str, Any]) -> dict[str, Any]:
    if len(value) > _MAX_METADATA_KEYS:
        raise ValueError("metadata contains too many keys")
    _validate_json_value(value)
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    if len(encoded.encode("utf-8")) > _MAX_METADATA_BYTES:
        raise ValueError("metadata is too large")
    copied = json.loads(encoded)
    if not isinstance(copied, dict):  # pragma: no cover - guarded by input type
        raise ValueError("metadata must be an object")
    return freeze_mapping(copied)


class ReportRequest(BaseModel):
    """Bounded request model for report generation intent."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    report_name: str = "analysis-report"
    format: str = "json"
    sections: tuple[str, ...] = ("summary",)
    max_items_per_section: int = Field(default=100, ge=1, le=10_000)
    metadata: dict[str, Any] = Field(default_factory=FrozenDict)

    @field_validator("report_name")
    @classmethod
    def _report_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned or len(cleaned) > _MAX_REPORT_NAME_LENGTH:
            raise ValueError("report_name must be 1-120 characters")
        return cleaned

    @field_validator("format")
    @classmethod
    def _format(cls, value: str) -> str:
        cleaned = value.strip().casefold()
        if cleaned not in _SUPPORTED_REPORT_FORMATS:
            raise ValueError("unsupported report format")
        return cleaned

    @field_validator("sections")
    @classmethod
    def _sections(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(
            dict.fromkeys(item.strip().casefold() for item in value if item.strip())
        )
        if not normalized:
            raise ValueError("at least one report section is required")
        if len(normalized) > _MAX_SECTIONS:
            raise ValueError(f"sections cannot contain more than {_MAX_SECTIONS} items")
        if any(item not in _SUPPORTED_REPORT_SECTIONS for item in normalized):
            raise ValueError("unsupported report section")
        return normalized

    @field_validator("metadata")
    @classmethod
    def _metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _safe_metadata(value)


class ReportManifest(BaseModel):
    """Stable metadata envelope for generated reports."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    report_id: UUID
    report_name: str
    format: str
    generated_at: datetime
    section_count: int = Field(ge=1, le=_MAX_SECTIONS)
    max_items_per_section: int = Field(ge=1, le=10_000)
    warnings: tuple[str, ...] = ()

    @field_validator("report_name")
    @classmethod
    def _manifest_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned or len(cleaned) > _MAX_REPORT_NAME_LENGTH:
            raise ValueError("report_name must be 1-120 characters")
        return cleaned

    @field_validator("format")
    @classmethod
    def _manifest_format(cls, value: str) -> str:
        cleaned = value.strip().casefold()
        if cleaned not in _SUPPORTED_REPORT_FORMATS:
            raise ValueError("unsupported report format")
        return cleaned


class ReportDocument(BaseModel):
    """Bounded report payload with deterministic metadata."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    manifest: ReportManifest
    content: str
    content_type: str
    file_name: str

    @field_validator("content")
    @classmethod
    def _content_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content must not be empty")
        return value

    @field_validator("content_type")
    @classmethod
    def _content_type(cls, value: str) -> str:
        cleaned = value.strip().casefold()
        if not cleaned or len(cleaned) > 120:
            raise ValueError("content_type must be 1-120 characters")
        return cleaned

    @field_validator("file_name")
    @classmethod
    def _file_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned or len(cleaned) > 255:
            raise ValueError("file_name must be 1-255 characters")
        return cleaned