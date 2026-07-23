from __future__ import annotations

from log_parser_engine.models import LogSeverity
from log_parser_engine.models.redis_event_classification import RedisEventClassification
from log_parser_engine.models.redis_record import RedisLogRecord


def classify_redis_event(
    record: RedisLogRecord,
    *,
    strict: bool = False,
) -> RedisEventClassification:
    message = record.message.lower()
    if "ready to accept connections" in message:
        return RedisEventClassification(
            category="lifecycle",
            event_type="redis.lifecycle.ready",
            severity=LogSeverity.INFO,
            summary="Redis is ready to accept connections.",
            matched_rule="READY_TO_ACCEPT_CONNECTIONS",
            attributes={"pid": record.pid},
        )
    if "master <-> replica sync started" in message:
        return RedisEventClassification(
            category="replication",
            event_type="redis.replication.sync_started",
            severity=LogSeverity.INFO,
            summary="Replication synchronization started.",
            matched_rule="REPLICA_SYNC_STARTED",
        )
    if "+sdown" in message:
        return RedisEventClassification(
            category="sentinel",
            event_type="redis.sentinel.subjective_down",
            severity=LogSeverity.WARNING,
            summary="Sentinel marked the master as subjectively down.",
            matched_rule="SUBJECTIVE_DOWN",
        )
    if "cluster state changed" in message:
        return RedisEventClassification(
            category="cluster",
            event_type="redis.cluster.state_ok",
            severity=LogSeverity.INFO,
            summary="Redis cluster state changed.",
            matched_rule="CLUSTER_STATE_CHANGED",
        )
    if "background saving started" in message:
        return RedisEventClassification(
            category="persistence",
            event_type="redis.persistence.bgsave_started",
            severity=LogSeverity.INFO,
            summary="Redis background save started.",
            matched_rule="BGSAVE_STARTED",
        )
    if "warning" in message:
        return RedisEventClassification(
            category="generic",
            event_type="redis.message",
            severity=LogSeverity.WARNING,
            summary="Redis emitted a warning.",
            matched_rule=None,
        )
    return RedisEventClassification(
        category="generic",
        event_type="redis.message",
        severity=LogSeverity.INFO,
        summary="Redis emitted a log message.",
        matched_rule=None,
    )
