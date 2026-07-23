from __future__ import annotations

from enum import Enum


class RedisRole(str, Enum):
    MASTER = "master"
    REPLICA = "replica"
    SENTINEL = "sentinel"
    CHILD = "child"
    UNKNOWN = "unknown"


ROLE_CODES: dict[str, str] = {
    "M": RedisRole.MASTER.value,
    "S": RedisRole.REPLICA.value,
    "X": RedisRole.SENTINEL.value,
    "C": RedisRole.CHILD.value,
    "A": RedisRole.CHILD.value,
    "R": RedisRole.UNKNOWN.value,
    "?": RedisRole.UNKNOWN.value,
}

LEVEL_MARKER_SEVERITY: dict[str, str] = {
    ".": "debug",
    "-": "info",
    "*": "info",
    "#": "warning",
}

MONTHS: dict[str, int] = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

STRONG_REDIS_MARKERS = (
    "ready to accept connections",
    "background saving started",
    "cluster state changed",
    "master <-> replica sync",
    "connecting to master",
    "sentinel",
)

KNOWN_PROCESS_NAMES = ("redis-server", "redis-sentinel")

PREFIX_PATTERNS = (
    "redis-server[",
    "redis-sentinel[",
    "redis-server:",
    "redis-sentinel:",
)
