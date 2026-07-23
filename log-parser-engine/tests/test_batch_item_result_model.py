from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from log_parser_engine.models import (
    BatchItem,
    BatchItemResult,
    LogEvent,
    LogSourceType,
    ParseResult,
    ParseStatus,
)


def _item() -> BatchItem:
    return BatchItem(
        index=1,
        source_line_start=1,
        source_line_end=1,
        raw_record="hello",
        record_type="data",
        character_count=5,
    )


def test_batch_item_result_success_validation() -> None:
    event = LogEvent(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        source_type=LogSourceType.application,
        message="ok",
        raw_message="ok",
    )
    parse_result = ParseResult(status=ParseStatus.success, events=[event])
    result = BatchItemResult(
        item=_item(),
        status="success",
        parser_name="fake",
        event=event,
        parse_result=parse_result,
    )
    assert result.status == "success"


def test_batch_item_result_failure_requires_error_or_parse_failure() -> None:
    with pytest.raises(ValidationError):
        BatchItemResult(item=_item(), status="failure")
