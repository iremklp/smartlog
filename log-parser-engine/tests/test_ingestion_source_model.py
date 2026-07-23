from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from log_parser_engine.models import IngestionSource


def test_ingestion_source_display_name_prefers_archive_entry() -> None:
    source = IngestionSource(
        kind="archive_entry",
        name="entry.log",
        path="/tmp/archive.zip",
        archive_name="archive.zip",
        archive_entry_name="entry.log",
        size_bytes=10,
    )

    assert source.display_name == "archive.zip:entry.log"


def test_ingestion_source_normalizes_extension_and_content_type() -> None:
    source = IngestionSource(
        kind="bytes",
        name=" sample.log ",
        path=None,
        extension=".LOG",
        content_type=" Text/Plain; charset=utf-8 ",
        size_bytes=1,
        modified_at=datetime.now(timezone.utc),
    )

    assert source.extension == "log"
    assert source.content_type == "text/plain"
    assert source.display_name == "sample.log"


def test_ingestion_source_rejects_invalid_archive_metadata() -> None:
    with pytest.raises(ValidationError):
        IngestionSource(
            kind="archive_entry",
            name="entry.log",
            path=None,
            archive_name=None,
            archive_entry_name=None,
            size_bytes=1,
        )
