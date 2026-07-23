from __future__ import annotations

from datetime import datetime, timezone

from log_parser_engine.batch.error_policy import ErrorPolicyEvaluator
from log_parser_engine.batch.options import BatchParseOptions
from log_parser_engine.models import (
    BatchItem,
    BatchItemResult,
    LogEvent,
    LogSourceType,
    ParseResult,
    ParseStatus,
)


def _success_result() -> BatchItemResult:
    item = BatchItem(
        index=1,
        source_line_start=1,
        source_line_end=1,
        raw_record="ok",
        record_type="data",
        character_count=2,
    )
    event = LogEvent(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        source_type=LogSourceType.application,
        message="ok",
        raw_message="ok",
    )
    return BatchItemResult(
        item=item,
        status="success",
        event=event,
        parse_result=ParseResult(status=ParseStatus.success, events=[event]),
    )


def _failure_result() -> BatchItemResult:
    item = BatchItem(
        index=1,
        source_line_start=1,
        source_line_end=1,
        raw_record="bad",
        record_type="data",
        character_count=3,
    )
    return BatchItemResult(
        item=item,
        status="failure",
        error_code="PARSE_FAILED",
        parse_result=ParseResult(status=ParseStatus.failed),
    )


def test_error_policy_stop_on_error() -> None:
    evaluator = ErrorPolicyEvaluator(BatchParseOptions(stop_on_error=True))
    decision = evaluator.evaluate_after_result(_failure_result())
    assert decision.stop is True
    assert decision.reason == "stop_on_error"


def test_error_policy_resets_consecutive_errors_on_success() -> None:
    evaluator = ErrorPolicyEvaluator(BatchParseOptions(max_consecutive_errors=2))
    assert evaluator.evaluate_after_result(_failure_result()).stop is False
    assert evaluator.evaluate_after_result(_success_result()).stop is False
    assert evaluator.evaluate_after_result(_failure_result()).stop is False
