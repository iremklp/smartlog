from __future__ import annotations

from types import MappingProxyType

SUPPORTED_ACCESS_VENDOR = ("apache", "nginx", "generic")
SUPPORTED_ERROR_VENDOR = ("apache", "nginx", "generic")

APACHE_COMMON_FORMAT = "combined"

COMMON_ACCESS_FIELDS = (
    "remote_addr",
    "remote_user",
    "time_local",
    "request",
    "status",
    "body_bytes_sent",
)

COMBINED_ACCESS_FIELDS = COMMON_ACCESS_FIELDS + ("http_referer", "http_user_agent")

APACHE_ERROR_PREFIXES = ("[error]", "[warn]", "[crit]", "[notice]")
NGINX_ERROR_PREFIXES = ("[error]", "[warn]", "[crit]", "[notice]")

HTTP_METHODS = frozenset({"get", "post", "put", "delete", "patch", "head", "options"})

SEVERITY_MAP = MappingProxyType(
    {
        "emerg": "critical",
        "alert": "critical",
        "crit": "critical",
        "error": "error",
        "warn": "warning",
        "notice": "notice",
        "info": "info",
        "debug": "debug",
    }
)

STATUS_CLASS_MAP = MappingProxyType(
    {
        "2": "success",
        "3": "redirect",
        "4": "client_error",
        "5": "server_error",
    }
)
