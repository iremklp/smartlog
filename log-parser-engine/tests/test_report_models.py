"""Foundation tests for report contract models."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from log_parser_engine.models import ReportDocument, ReportManifest, ReportRequest


def test_report_request_defaults_and_normalization() -> None:
    request = ReportRequest(
        report_name="  Weekly Summary  ",
        format=" JSON ",
        sections=("summary", "summary", " timeline "),
    )

    assert request.report_name == "Weekly Summary"
    assert request.format == "json"
    assert request.sections == ("summary", "timeline")
    assert request.max_items_per_section == 100


def test_report_request_rejects_unsupported_format_and_sections() -> None:
    with pytest.raises(ValidationError, match="unsupported report format"):
        ReportRequest(format="pdf")

    with pytest.raises(ValidationError, match="unsupported report section"):
        ReportRequest(sections=("summary", "private_notes"))


def test_report_request_metadata_is_json_safe_and_immutable() -> None:
    request = ReportRequest(metadata={"nested": {"items": [1, 2, 3]}})

    assert request.metadata["nested"]["items"] == (1, 2, 3)
    with pytest.raises(TypeError, match="mutation"):
        request.metadata["new"] = True
    with pytest.raises(TypeError, match="mutation"):
        request.metadata["nested"]["new"] = True

    with pytest.raises(ValidationError, match="JSON-safe"):
        ReportRequest(metadata={"value": object()})


def test_report_manifest_and_document_validation() -> None:
    manifest = ReportManifest(
        report_id=uuid4(),
        report_name="Ops Report",
        format="markdown",
        generated_at=datetime.now(timezone.utc),
        section_count=2,
        max_items_per_section=100,
        warnings=("truncated samples",),
    )
    document = ReportDocument(
        manifest=manifest,
        content="# Ops Report\n\nAll good.",
        content_type="text/markdown",
        file_name="ops-report.md",
    )

    assert document.manifest.format == "markdown"
    assert document.file_name == "ops-report.md"

    with pytest.raises(ValidationError, match="content must not be empty"):
        ReportDocument(
            manifest=manifest,
            content="   ",
            content_type="text/markdown",
            file_name="ops-report.md",
        )