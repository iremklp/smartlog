from __future__ import annotations

from types import MappingProxyType

SUPPORTED_PROFILES = (
    "generic",
    "ecs",
    "opentelemetry",
    "serilog",
    "nlog",
    "log4j",
    "bunyan",
    "pino",
    "docker",
    "kubernetes",
)

PROFILE_SIGNAL_FIELDS = MappingProxyType(
    {
        "generic": ("timestamp", "level", "message", "service"),
        "ecs": ("@timestamp", "log.level", "service.name", "event.action"),
        "opentelemetry": ("timestamp", "severity_text", "body", "resource"),
        "serilog": ("@t", "@l", "@m", "SourceContext"),
        "nlog": ("time", "level", "message", "logger"),
        "log4j": ("timeMillis", "level", "message", "loggerName"),
        "bunyan": ("time", "level", "msg", "name"),
        "pino": ("time", "level", "msg", "name"),
        "docker": ("log", "stream", "time"),
        "kubernetes": ("kubernetes", "container", "stream", "log"),
    }
)

GENERIC_DEFAULT_PATHS = MappingProxyType(
    {
        "timestamp": ("timestamp", "time", "datetime"),
        "severity": ("level", "severity", "log.level"),
        "message": ("message", "msg", "body"),
        "event_type": ("event_type", "event.type"),
        "service": ("service", "service.name"),
        "application": ("application", "app"),
        "environment": ("environment", "env"),
        "host": ("host", "host.name", "hostname"),
        "source": ("source", "logger", "loggerName", "SourceContext"),
        "trace_id": ("trace_id", "trace.id", "TraceId"),
        "correlation_id": ("correlation_id", "correlation.id"),
        "user_id": ("user_id", "user.id"),
        "client_ip": ("client_ip", "client.ip"),
        "server_ip": ("server_ip", "server.ip"),
        "http_method": ("http_method", "http.request.method"),
        "http_path": ("http_path", "url.path", "http.request.path"),
        "http_status": ("http_status", "http.response.status_code"),
        "duration_ms": ("duration_ms", "duration", "elapsed"),
        "tags": ("tags", "tag"),
        "attributes": ("attributes", "context"),
    }
)

SEVERITY_NUMBER_MAP = MappingProxyType(
    {
        0: "trace",
        1: "fatal",
        2: "error",
        3: "warning",
        4: "info",
        5: "debug",
    }
)

MAX_DETECTION_SAMPLE_LENGTH = 5000
RESERVED_CANONICAL_FIELDS = frozenset(
    {
        "timestamp",
        "severity",
        "message",
        "event_type",
        "service",
        "application",
        "environment",
        "host",
        "source",
        "trace_id",
        "correlation_id",
        "user_id",
        "client_ip",
        "server_ip",
        "http_method",
        "http_path",
        "http_status",
        "duration_ms",
        "tags",
        "attributes",
    }
)
PROTECTED_JSON_PATHS = frozenset(
    {"timestamp", "message", "level", "severity", "service"}
)
