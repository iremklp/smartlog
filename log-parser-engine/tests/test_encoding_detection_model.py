from __future__ import annotations

import pytest
from pydantic import ValidationError

from log_parser_engine.models import EncodingDetection


def test_encoding_detection_normalizes_and_deduplicates() -> None:
    detection = EncodingDetection(
        encoding="UTF-8",
        confidence=0.95,
        source="bom",
        bom="UTF-8",
        is_ascii=True,
        alternatives=("utf-8", "latin1", "latin1"),
        notes=("BOM", "bom"),
    )

    assert detection.encoding == "utf-8"
    assert detection.bom == "utf-8"
    assert detection.alternatives == ("utf-8", "latin1")
    assert detection.notes == ("bom",)
    assert detection.certain is True


def test_encoding_detection_rejects_invalid_confidence() -> None:
    with pytest.raises(ValidationError):
        EncodingDetection(
            encoding="utf-8",
            confidence=1.5,
            source="utf8",
        )
