from __future__ import annotations

from collections.abc import Sequence
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

from log_parser_engine.analysis import AnalysisOptions
from log_parser_engine.batch import BatchParseOptions
from log_parser_engine.plugins import PluginStartupOptions
from log_parser_engine.storage import EventStoreOptions


class ApplicationOptions(BaseModel):
    """Immutable top-level application configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(default="log-parser-engine")
    enable_builtin_parsers: bool = True
    plugin_startup_options: PluginStartupOptions = Field(
        default_factory=PluginStartupOptions
    )
    parser_minimum_confidence: float = 0.60
    parser_ambiguity_margin: float = 0.05
    event_store_options: EventStoreOptions = Field(default_factory=EventStoreOptions)
    batch_parse_options: BatchParseOptions = Field(default_factory=BatchParseOptions)
    analysis_options: AnalysisOptions = Field(default_factory=AnalysisOptions)
    max_concurrent_analysis_operations: int = Field(default=2, ge=1, le=64)
    max_analysis_request_body_bytes: int = Field(
        default=65_536,
        ge=256,
        le=1_048_576,
    )
    max_upload_bytes: int = Field(
        default=50 * 1024 * 1024,
        ge=1,
        le=1024 * 1024 * 1024,
    )
    cors_allowed_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )
    trust_incoming_request_id: bool = False

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("name must not be empty")
        return cleaned

    @field_validator("parser_minimum_confidence", "parser_ambiguity_margin")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence value must be between 0.0 and 1.0")
        return value

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def normalize_cors_origins(cls, value: object) -> tuple[str, ...]:
        if isinstance(value, str) or not isinstance(value, Sequence):
            raise ValueError("cors_allowed_origins must be a sequence of origins")

        origins: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                raise ValueError("CORS origins must be strings")
            origin = item.strip().rstrip("/")
            if not origin:
                continue
            cls._validate_cors_origin(origin)
            if origin not in seen:
                origins.append(origin)
                seen.add(origin)
        return tuple(origins)

    @staticmethod
    def _validate_cors_origin(origin: str) -> None:
        if origin == "*":
            raise ValueError("wildcard CORS origins are not allowed")
        parsed = urlsplit(origin)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("CORS origins must be HTTP(S) origins without paths")
