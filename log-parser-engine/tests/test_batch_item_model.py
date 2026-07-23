from __future__ import annotations

import pytest
from pydantic import ValidationError

from log_parser_engine.models import BatchItem


def test_batch_item_line_span() -> None:
    item = BatchItem(
        index=2,
        source_line_start=10,
        source_line_end=12,
        raw_record="abc",
        record_type="data",
        character_count=3,
    )
    assert item.line_span == 3


def test_batch_item_requires_preview_when_raw_missing() -> None:
    with pytest.raises(ValidationError):
        BatchItem(
            index=1,
            source_line_start=1,
            source_line_end=1,
            raw_record=None,
            raw_record_preview=None,
            record_type="data",
            character_count=4,
        )
