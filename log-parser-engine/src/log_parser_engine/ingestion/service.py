from __future__ import annotations

from pathlib import Path

from log_parser_engine.exceptions import (
    BinaryContentError,
    EmptyContentError,
    InputTooLargeError,
)
from log_parser_engine.models import (
    ArchiveEntryInfo,
    EncodingDetection,
    IngestionMetadata,
    IngestionResult,
    IngestionSource,
    IngestionWarning,
)

from .archive import extract_logical_document
from .binary import BinaryAssessment, assess_binary_content
from .encoding import decode_text, detect_encoding
from .hashing import compute_sha256_hex
from .helpers import guess_content_type, split_name_parts
from .line_endings import LineEndingAnalysis, analyze_line_endings
from .options import IngestionOptions
from .source_reader import build_source_from_bytes, read_path_bytes


class FileIngestionService:
    """Prepare a single logical text document for downstream parsing."""

    def ingest_path(
        self,
        path: str | Path,
        *,
        options: IngestionOptions | None = None,
    ) -> IngestionResult:
        resolved_options = options or IngestionOptions()
        raw_bytes, source = read_path_bytes(path, options=resolved_options)
        return self._ingest_bytes_internal(
            raw_bytes,
            source=source,
            options=resolved_options,
        )

    def ingest_bytes(
        self,
        data: bytes,
        *,
        source_name: str | None = None,
        options: IngestionOptions | None = None,
    ) -> IngestionResult:
        resolved_options = options or IngestionOptions()
        source = build_source_from_bytes(data, source_name=source_name)
        return self._ingest_bytes_internal(
            data,
            source=source,
            options=resolved_options,
        )

    def ingest_text(
        self,
        text: str,
        *,
        source_name: str | None = None,
        options: IngestionOptions | None = None,
    ) -> IngestionResult:
        resolved_options = options or IngestionOptions()
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        if not text and not resolved_options.allow_empty:
            raise EmptyContentError("empty content is not allowed")

        _, extension = split_name_parts(source_name)

        source = IngestionSource(
            kind="text",
            name=source_name,
            path=None,
            extension=extension,
            content_type=guess_content_type(source_name),
            size_bytes=len(text.encode("utf-8")),
            modified_at=None,
        )
        line_info = analyze_line_endings(text)
        raw_bytes = text.encode("utf-8")
        sha256 = (
            compute_sha256_hex(raw_bytes)
            if resolved_options.compute_sha256
            else None
        )
        warnings: tuple[IngestionWarning, ...] = ()
        if not text:
            warnings = (
                IngestionWarning(
                    code="EMPTY_CONTENT_ALLOWED",
                    message="empty text input was accepted",
                    details={"source_name": source.display_name},
                    recoverable=True,
                ),
            )
        encoding = EncodingDetection(
            encoding="utf-8",
            confidence=1.0,
            source="text",
            bom=None,
            is_ascii=all(ord(char) < 128 for char in text),
            alternatives=(),
            notes=("text_input",),
        )
        metadata = IngestionMetadata(
            source=source,
            encoding=encoding,
            raw_size_bytes=len(raw_bytes),
            decoded_character_count=len(text),
            line_count=line_info.line_count,
            line_ending=line_info.line_ending,
            has_trailing_newline=line_info.has_trailing_newline,
            is_binary_like=False,
            null_byte_count=0,
            control_character_count=0,
            sha256=sha256,
            archive_type=None,
            compressed_size_bytes=None,
            decompressed_size_bytes=len(raw_bytes),
            selected_archive_entry=None,
            warnings=warnings,
            attributes={"line_ending_counts": {
                "lf": line_info.lf_count,
                "crlf": line_info.crlf_count,
                "cr": line_info.cr_count,
            }},
        )
        return IngestionResult(text=text, metadata=metadata, original_bytes=None)

    def _ingest_bytes_internal(
        self,
        data: bytes,
        *,
        source: IngestionSource,
        options: IngestionOptions,
    ) -> IngestionResult:
        if len(data) > options.max_input_bytes:
            raise InputTooLargeError("input exceeds configured limit")
        if not data and not options.allow_empty:
            raise EmptyContentError("empty content is not allowed")

        (
            logical_bytes,
            source,
            archive_type,
            compressed_size,
            selected_archive_entry,
        ) = extract_logical_document(
            data, source, options=options
        )
        raw_bytes = logical_bytes

        if not raw_bytes and not options.allow_empty:
            raise EmptyContentError("empty content is not allowed")

        assessment = assess_binary_content(raw_bytes)
        detection = detect_encoding(raw_bytes, options=options)
        binary_like = assessment.is_binary_like and detection.bom is None
        if binary_like and not options.allow_binary:
            raise BinaryContentError("binary-like content is not allowed")

        text = decode_text(raw_bytes, detection=detection, options=options)

        if not text and not options.allow_empty:
            raise EmptyContentError("empty content is not allowed")

        if options.normalize_newlines:
            text = text.replace("\r\n", "\n").replace("\r", "\n")

        line_info = analyze_line_endings(text)
        sha256 = compute_sha256_hex(raw_bytes) if options.compute_sha256 else None
        warnings = self._build_warnings(
            detection=detection,
            assessment=assessment,
            source=source,
            options=options,
            selected_archive_entry=selected_archive_entry,
            line_info=line_info,
        )
        metadata = IngestionMetadata(
            source=source,
            encoding=detection,
            raw_size_bytes=len(data),
            decoded_character_count=len(text),
            line_count=line_info.line_count,
            line_ending=line_info.line_ending,
            has_trailing_newline=line_info.has_trailing_newline,
            is_binary_like=binary_like,
            null_byte_count=assessment.null_byte_count,
            control_character_count=assessment.control_character_count,
            sha256=sha256,
            archive_type=archive_type,
            compressed_size_bytes=compressed_size,
            decompressed_size_bytes=len(raw_bytes),
            selected_archive_entry=selected_archive_entry,
            warnings=warnings,
            attributes={
                "binary_signals": assessment.signals,
                "encoding_notes": detection.notes,
            },
        )
        original_bytes = raw_bytes if options.preserve_original_bytes else None
        return IngestionResult(
            text=text,
            metadata=metadata,
            original_bytes=original_bytes,
        )

    def _build_warnings(
        self,
        *,
        detection: EncodingDetection,
        assessment: BinaryAssessment,
        source: IngestionSource,
        options: IngestionOptions,
        selected_archive_entry: ArchiveEntryInfo | None,
        line_info: LineEndingAnalysis,
    ) -> tuple[IngestionWarning, ...]:
        warnings: list[IngestionWarning] = []
        if not detection.certain:
            warnings.append(
                IngestionWarning(
                    code="ENCODING_LOW_CONFIDENCE",
                    message=(
                        "encoding detection confidence is below the certainty threshold"
                    ),
                    details={"confidence": detection.confidence},
                    recoverable=True,
                )
            )
        if detection.source == "fallback":
            warnings.append(
                IngestionWarning(
                    code="ENCODING_FALLBACK_USED",
                    message="fallback encoding was used",
                    details={"encoding": detection.encoding},
                    recoverable=True,
                )
            )
        if assessment.is_binary_like and options.allow_binary:
            warnings.append(
                IngestionWarning(
                    code="BINARY_LIKE_CONTENT_ALLOWED",
                    message="binary-like content was allowed by options",
                    details={"source_name": source.display_name},
                    recoverable=True,
                )
            )
        if line_info.line_ending == "mixed":
            warnings.append(
                IngestionWarning(
                    code="MIXED_LINE_ENDINGS",
                    message="mixed line endings were detected",
                    details={"line_count": line_info.line_count},
                    recoverable=True,
                )
            )
        if selected_archive_entry is not None:
            warnings.append(
                IngestionWarning(
                    code="ARCHIVE_ENTRY_AUTO_SELECTED",
                    message="archive entry was auto-selected",
                    details={"archive_entry_name": selected_archive_entry.name},
                    recoverable=True,
                )
            )
        if source.content_type is None:
            warnings.append(
                IngestionWarning(
                    code="UNKNOWN_CONTENT_TYPE",
                    message="content type could not be inferred",
                    details={"source_name": source.display_name},
                    recoverable=True,
                )
            )
        return tuple(warnings)
