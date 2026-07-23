from __future__ import annotations

from log_parser_engine.models.redis_event_classification import RedisEventClassification
from log_parser_engine.models.redis_record import RedisLogRecord


def map_redis_record_to_normalization_fields(
    record: RedisLogRecord,
    classification: RedisEventClassification,
) -> dict[str, object]:
    redis_attributes: dict[str, object] = {
        "pid": record.pid,
        "role": record.role,
        "role_code": record.role_code,
        "level_marker": record.level_marker,
        "category": classification.category,
        "matched_rule": classification.matched_rule,
        "timestamp_source": record.timestamp_source,
        "outer_host": record.outer_host,
        "outer_process": record.outer_process,
        "raw_line": record.raw_line,
    }
    attributes: dict[str, object] = {
        "redis": redis_attributes,
        "redis_event": dict(classification.attributes),
    }
    if record.outer_timestamp is not None:
        redis_attributes["outer_timestamp"] = record.outer_timestamp
    if record.attributes:
        redis_attributes["parser_attributes"] = dict(record.attributes)
    service = "redis-sentinel" if record.role == "sentinel" else "redis"
    tags = ["redis", classification.category]
    if record.role:
        tags.append(record.role)
    if classification.category == "sentinel":
        tags.append("sentinel")
    if classification.category == "cluster":
        tags.append("cluster")
    if classification.category == "replication":
        tags.append("replication")
    if classification.category == "persistence":
        tags.append("persistence")

    return {
        "timestamp": record.timestamp,
        "severity": classification.severity,
        "event_type": classification.event_type,
        "message": classification.summary,
        "host": record.outer_host,
        "source": record.outer_process or "redis-server",
        "service": service,
        "application": "redis",
        "attributes": attributes,
        "tags": tags,
    }
