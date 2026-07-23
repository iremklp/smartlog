from __future__ import annotations

from datetime import datetime, timezone

from log_parser_engine.exceptions import RedisTimestampError

from .constants import MONTHS


def parse_redis_timestamp(
    value: str,
    *,
    default_timezone: str = "UTC",
    reference_datetime: datetime | None = None,
) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise RedisTimestampError("timestamp must not be empty")

    cleaned = value.strip()
    parts = cleaned.split()
    if len(parts) < 3:
        raise RedisTimestampError("invalid redis timestamp")

    try:
        day = int(parts[0])
        month = MONTHS[parts[1].lower()]
    except (ValueError, KeyError, IndexError) as exc:
        raise RedisTimestampError("invalid redis timestamp") from exc

    if len(parts) >= 4 and parts[2].isdigit():
        year = int(parts[2])
        time_part = parts[3]
    elif len(parts) >= 3:
        year = (
            reference_datetime.year
            if reference_datetime is not None
            else datetime.now(timezone.utc).year
        )
        time_part = parts[2]
    else:
        raise RedisTimestampError("invalid redis timestamp")

    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            parsed = datetime.strptime(
                f"{year:04d}-{month:02d}-{day:02d} {time_part}",
                fmt,
            )
            return _normalize(parsed, default_timezone)
        except ValueError:
            continue
    raise RedisTimestampError("invalid redis timestamp")


def parse_outer_timestamp(
    value: str,
    *,
    default_timezone: str = "UTC",
    reference_datetime: datetime | None = None,
) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise RedisTimestampError("timestamp must not be empty")

    cleaned = value.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError:
        try:
            parsed = datetime.strptime(cleaned, "%b %d %H:%M:%S")
            if reference_datetime is not None:
                parsed = parsed.replace(year=reference_datetime.year)
        except ValueError as exc:
            raise RedisTimestampError("invalid outer timestamp") from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _normalize(value: datetime, default_timezone: str) -> datetime:
    if value.tzinfo is None:
        if default_timezone.upper() == "UTC":
            value = value.replace(tzinfo=timezone.utc)
        else:
            from zoneinfo import ZoneInfo

            value = value.replace(tzinfo=ZoneInfo(default_timezone))
    return value.astimezone(timezone.utc)
