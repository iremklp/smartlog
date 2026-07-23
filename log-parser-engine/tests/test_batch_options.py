from __future__ import annotations

import pytest
from pydantic import ValidationError

from log_parser_engine.batch import BatchParseOptions


def test_batch_options_defaults() -> None:
    options = BatchParseOptions()
    assert options.record_mode == "auto"
    assert options.detect_once is True
    assert options.max_record_characters == 1024 * 1024
    assert options.skip_blank_records is True


def test_batch_options_validates_conflicts() -> None:
    with pytest.raises(ValidationError):
        BatchParseOptions(preserve_blank_records=True, skip_blank_records=True)


def test_batch_options_validates_threshold() -> None:
    with pytest.raises(ValidationError):
        BatchParseOptions(error_rate_threshold=1.5)
