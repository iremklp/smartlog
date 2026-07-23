from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class JsonFieldMapping(BaseModel):
    """Configurable field-path mapping for canonical JSON log fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp_paths: tuple[str, ...] = Field(default_factory=tuple)
    severity_paths: tuple[str, ...] = Field(default_factory=tuple)
    message_paths: tuple[str, ...] = Field(default_factory=tuple)
    event_type_paths: tuple[str, ...] = Field(default_factory=tuple)
    service_paths: tuple[str, ...] = Field(default_factory=tuple)
    application_paths: tuple[str, ...] = Field(default_factory=tuple)
    environment_paths: tuple[str, ...] = Field(default_factory=tuple)
    host_paths: tuple[str, ...] = Field(default_factory=tuple)
    source_paths: tuple[str, ...] = Field(default_factory=tuple)
    trace_id_paths: tuple[str, ...] = Field(default_factory=tuple)
    correlation_id_paths: tuple[str, ...] = Field(default_factory=tuple)
    user_id_paths: tuple[str, ...] = Field(default_factory=tuple)
    client_ip_paths: tuple[str, ...] = Field(default_factory=tuple)
    server_ip_paths: tuple[str, ...] = Field(default_factory=tuple)
    http_method_paths: tuple[str, ...] = Field(default_factory=tuple)
    http_path_paths: tuple[str, ...] = Field(default_factory=tuple)
    http_status_paths: tuple[str, ...] = Field(default_factory=tuple)
    duration_ms_paths: tuple[str, ...] = Field(default_factory=tuple)
    tags_paths: tuple[str, ...] = Field(default_factory=tuple)
    attributes_paths: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator(*[field for field in __annotations__ if field.endswith("_paths")])
    @classmethod
    def normalize_paths(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            cleaned = str(item).strip()
            if not cleaned:
                continue
            if cleaned not in seen:
                normalized.append(cleaned)
                seen.add(cleaned)
        return tuple(normalized)

    @property
    def configured_field_count(self) -> int:
        count = 0
        for field_name, value in self.model_dump().items():
            if field_name.endswith("_paths") and value:
                count += len(value)
        return count

    @classmethod
    def generic_defaults(cls) -> "JsonFieldMapping":
        from .json_field_mapping import JsonFieldMapping as Current  # noqa: PLC0415

        return Current(
            timestamp_paths=("timestamp", "time", "datetime"),
            severity_paths=("level", "severity", "log.level"),
            message_paths=("message", "msg", "body"),
            event_type_paths=("event_type", "event.type"),
            service_paths=("service", "service.name"),
            application_paths=("application", "app"),
            environment_paths=("environment", "env"),
            host_paths=("host", "host.name", "hostname"),
            source_paths=("source", "logger", "loggerName", "SourceContext"),
            trace_id_paths=("trace_id", "trace.id", "TraceId"),
            correlation_id_paths=("correlation_id", "correlation.id"),
            user_id_paths=("user_id", "user.id"),
            client_ip_paths=("client_ip", "client.ip"),
            server_ip_paths=("server_ip", "server.ip"),
            http_method_paths=("http_method", "http.request.method"),
            http_path_paths=("http_path", "url.path", "http.request.path"),
            http_status_paths=("http_status", "http.response.status_code"),
            duration_ms_paths=("duration_ms", "duration", "elapsed"),
            tags_paths=("tags", "tag"),
            attributes_paths=("attributes", "context"),
        )
