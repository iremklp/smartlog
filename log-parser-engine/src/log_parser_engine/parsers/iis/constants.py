from __future__ import annotations

from types import MappingProxyType

DIRECTIVE_PREFIX = "#"
NULL_MARKER = "-"
KNOWN_DIRECTIVES = frozenset({"software", "version", "date", "fields"})
KNOWN_IIS_FIELD_ALIASES = MappingProxyType(
    {
        "date": "date",
        "time": "time",
        "s-ip": "s-ip",
        "s-port": "s-port",
        "cs-method": "cs-method",
        "cs-uri-stem": "cs-uri-stem",
        "cs-uri-query": "cs-uri-query",
        "cs-username": "cs-username",
        "c-ip": "c-ip",
        "sc-status": "sc-status",
        "sc-substatus": "sc-substatus",
        "sc-win32-status": "sc-win32-status",
        "time-taken": "time-taken",
        "cs(user-agent)": "cs(user-agent)",
        "cs(referer)": "cs(referer)",
        "cs(cookie)": "cs(cookie)",
        "cs-host": "cs-host",
        "cs-bytes": "cs-bytes",
        "sc-bytes": "sc-bytes",
        "cs-version": "cs-version",
        "cs-protocol": "cs-protocol",
        "s-computername": "s-computername",
        "s-sitename": "s-sitename",
    }
)
HTTP_STATUS_TO_SEVERITY = MappingProxyType(
    {
        401: "warning",
        403: "warning",
        404: "warning",
        500: "error",
        502: "error",
        503: "error",
    }
)
