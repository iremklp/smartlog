from __future__ import annotations

from log_parser_engine.batch.buffering import DetectionSampleBuffer
from log_parser_engine.batch.record_reader import SourceRecord


def test_detection_sample_buffer_collects_data_records() -> None:
    buffer = DetectionSampleBuffer(max_records=2, max_characters=10)
    first = SourceRecord(1, 1, 1, "abc", "abc", 3, False, "data")
    second = SourceRecord(2, 2, 2, "def", "def", 3, False, "data")

    assert buffer.add(first) is True
    assert buffer.add(second) is True
    assert buffer.full is True
    assert buffer.build_sample() == "abc\ndef"
