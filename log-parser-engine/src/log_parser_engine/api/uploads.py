from __future__ import annotations

from fastapi import UploadFile

from log_parser_engine.exceptions import EmptyContentError, InputTooLargeError

DEFAULT_UPLOAD_CHUNK_SIZE = 64 * 1024


async def read_bounded_upload(
    upload: UploadFile,
    *,
    max_bytes: int,
    chunk_size: int = DEFAULT_UPLOAD_CHUNK_SIZE,
) -> bytes:
    """Read and close an upload without issuing an unbounded read."""

    payload = bytearray()
    try:
        if max_bytes < 1:
            raise ValueError("max_bytes must be 1 or greater")
        if chunk_size < 1:
            raise ValueError("chunk_size must be 1 or greater")

        while True:
            remaining_with_overflow_probe = max_bytes + 1 - len(payload)
            requested_bytes = min(chunk_size, remaining_with_overflow_probe)
            chunk = await upload.read(requested_bytes)
            if not chunk:
                break
            payload.extend(chunk)
            if len(payload) > max_bytes:
                raise InputTooLargeError(
                    f"uploaded file exceeds the configured {max_bytes}-byte limit"
                )

        if not payload:
            raise EmptyContentError("uploaded file is empty")
        return bytes(payload)
    finally:
        await upload.close()
