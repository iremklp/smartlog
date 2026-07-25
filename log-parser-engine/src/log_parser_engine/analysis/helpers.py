from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from hashlib import sha256
from typing import Any


@dataclass(slots=True)
class RunningStatistics:
    """Constant-memory descriptive statistics using Welford's algorithm."""

    count: int = 0
    total: float = 0.0
    minimum: float | None = None
    maximum: float | None = None
    _mean: float = 0.0
    _m2: float = 0.0

    def add(self, value: float) -> None:
        if not math.isfinite(value):
            raise ValueError("running statistic values must be finite")
        self.count += 1
        self.total += value
        self.minimum = value if self.minimum is None else min(self.minimum, value)
        self.maximum = value if self.maximum is None else max(self.maximum, value)
        delta = value - self._mean
        self._mean += delta / self.count
        self._m2 += delta * (value - self._mean)

    @property
    def mean(self) -> float | None:
        return self._mean if self.count else None

    @property
    def population_standard_deviation(self) -> float | None:
        if not self.count:
            return None
        return math.sqrt(max(self._m2 / self.count, 0.0))


def enum_text(value: object) -> str | None:
    """Return a stable text representation for an enum or scalar value."""
    if value is None:
        return None
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    return None


def normalized_text(value: object) -> str | None:
    """Normalize a scalar grouping value without stringifying containers."""
    text = enum_text(value)
    if text is None:
        return None
    cleaned = text.strip()
    return cleaned or None


def safe_ratio(numerator: int | float, denominator: int | float) -> float:
    """Return a finite ratio, using zero when there is no denominator."""
    if denominator <= 0:
        return 0.0
    result = float(numerator) / float(denominator)
    return result if math.isfinite(result) else 0.0


def safe_mean(total: int | float, count: int) -> float | None:
    """Return a finite arithmetic mean when at least one sample exists."""
    if count <= 0:
        return None
    result = float(total) / count
    return result if math.isfinite(result) else None


def finite_float(value: object) -> float | None:
    """Convert a numeric scalar to float, rejecting booleans and non-finite values."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    converted = float(value)
    return converted if math.isfinite(converted) else None


def utc_datetime(value: datetime) -> datetime:
    """Normalize an aware datetime to UTC."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return value.astimezone(timezone.utc)


def epoch_aligned_start(value: datetime, bucket_seconds: int) -> datetime:
    """Return the UTC, Unix-epoch-aligned start of the containing bucket."""
    if bucket_seconds <= 0:
        raise ValueError("bucket_seconds must be positive")
    current = utc_datetime(value)
    epoch_seconds = math.floor(current.timestamp())
    aligned = epoch_seconds - (epoch_seconds % bucket_seconds)
    return datetime.fromtimestamp(aligned, tz=timezone.utc)


def bucket_end(start: datetime, bucket_seconds: int) -> datetime:
    """Return the exclusive end of a fixed-width bucket."""
    return start + timedelta(seconds=bucket_seconds)


def bounded_preview(value: str | None, *, limit: int = 200) -> str | None:
    """Return a single-line bounded preview without control characters."""
    if value is None:
        return None
    if limit <= 0:
        raise ValueError("limit must be positive")
    cleaned = "".join(
        character if character >= " " and character != "\x7f" else " "
        for character in value
    )
    cleaned = " ".join(cleaned.split())
    if len(cleaned) <= limit:
        return cleaned
    if limit == 1:
        return "…"
    return f"{cleaned[: limit - 1]}…"


def bounded_dimension(value: str | None, *, limit: int = 256) -> str | None:
    """Return a bounded dimension key while preserving deterministic uniqueness."""

    normalized = bounded_preview(value, limit=max(limit, 1))
    if value is None or normalized is None:
        return None
    cleaned = " ".join(value.split())
    if len(cleaned) <= limit:
        return normalized
    digest = sha256(cleaned.encode("utf-8")).hexdigest()[:16]
    suffix = f"…#{digest}"
    prefix_length = max(limit - len(suffix), 0)
    return f"{cleaned[:prefix_length]}{suffix}"[:limit]


def json_safe_scalar(value: object) -> str | int | float | bool | None:
    """Return a JSON scalar or ``None`` for unsupported complex values."""
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    if isinstance(value, Enum):
        return normalized_text(value)
    return None


def normalized_unique(values: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    """Trim and de-duplicate strings while preserving their first order."""
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = value.strip()
        if cleaned and cleaned not in seen:
            result.append(cleaned)
            seen.add(cleaned)
    return tuple(result)


def public_attributes(data: dict[str, Any]) -> dict[str, Any]:
    """Copy a mapping while dropping private/dunder keys."""
    return {
        key: value
        for key, value in data.items()
        if isinstance(key, str) and key and not key.startswith("__")
    }
