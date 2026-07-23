from __future__ import annotations

from typing import Any, Callable

from log_parser_engine.exceptions import EncodingDetectionError, TextDecodingError
from log_parser_engine.models import EncodingDetection

from .bom import detect_bom
from .helpers import dedupe_strings, normalize_codec_name
from .options import IngestionOptions

_charset_normalizer_from_bytes: Callable[[bytes], Any] | None

try:  # optional and controlled
    from charset_normalizer import from_bytes as _charset_normalizer_from_bytes_import
except Exception:  # noqa: BLE001
    _charset_normalizer_from_bytes = None
else:
    _charset_normalizer_from_bytes = _charset_normalizer_from_bytes_import


def detect_encoding(
    data: bytes,
    *,
    options: IngestionOptions,
) -> EncodingDetection:
    bom_encoding, bom_name, bom_length = detect_bom(data)
    if options.encoding is not None:
        return EncodingDetection(
            encoding=options.encoding,
            confidence=1.0,
            source="forced",
            bom=bom_name,
            is_ascii=_is_ascii(data),
            alternatives=(),
            notes=("forced_encoding",),
        )

    if bom_encoding is not None:
        return EncodingDetection(
            encoding=bom_encoding,
            confidence=1.0,
            source="bom",
            bom=bom_name,
            is_ascii=_is_ascii(data[bom_length:]),
            alternatives=(),
            notes=("bom_detected",),
        )

    if options.detect_encoding:
        utf8_result = _try_utf8(data)
        if utf8_result is not None:
            return utf8_result

        if _charset_normalizer_from_bytes is not None:
            detector_result = _try_charset_normalizer(data, options)
            if detector_result is not None:
                return detector_result

    fallback_result = _try_fallbacks(data, options)
    if fallback_result is not None:
        return fallback_result

    raise EncodingDetectionError("unable to detect a safe text encoding")


def decode_text(
    data: bytes,
    *,
    detection: EncodingDetection,
    options: IngestionOptions,
) -> str:
    codec = detection.encoding
    decode_bytes = data
    if detection.bom is not None and options.strip_bom:
        _, _, bom_length = detect_bom(data)
        decode_bytes = data[bom_length:]
    if detection.bom == "utf-8" and not options.strip_bom:
        codec = "utf-8"
    try:
        return decode_bytes.decode(codec, errors=options.encoding_errors)
    except UnicodeDecodeError as exc:
        raise TextDecodingError("text could not be decoded") from exc


def _try_utf8(data: bytes) -> EncodingDetection | None:
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return EncodingDetection(
        encoding="utf-8",
        confidence=1.0,
        source="utf8",
        bom=None,
        is_ascii=_is_ascii(data),
        alternatives=(),
        notes=("utf8_valid",),
    )


def _try_charset_normalizer(
    data: bytes,
    options: IngestionOptions,
) -> EncodingDetection | None:
    if _charset_normalizer_from_bytes is None:
        return None
    result = _charset_normalizer_from_bytes(data).best()
    if result is None:
        return None
    encoding = normalize_codec_name(result.encoding)
    if encoding is None:
        return None
    confidence = float(getattr(result, "confidence", 0.0))
    if confidence < options.encoding_confidence_threshold:
        return None
    alternatives = dedupe_strings(tuple(getattr(result, "alternatives", ()) or ()))
    notes = ("charset_normalizer",)
    return EncodingDetection(
        encoding=encoding,
        confidence=min(max(confidence, 0.0), 1.0),
        source="detector",
        bom=None,
        is_ascii=_is_ascii(data),
        alternatives=alternatives,
        notes=notes,
    )


def _try_fallbacks(data: bytes, options: IngestionOptions) -> EncodingDetection | None:
    for encoding in options.effective_fallback_encodings:
        try:
            data.decode(encoding)
        except UnicodeDecodeError:
            continue
        alternatives = tuple(
            candidate
            for candidate in options.effective_fallback_encodings
            if candidate != encoding
        )
        return EncodingDetection(
            encoding=encoding,
            confidence=0.60,
            source="fallback",
            bom=None,
            is_ascii=_is_ascii(data),
            alternatives=alternatives,
            notes=("fallback_used",),
        )
    return None


def _is_ascii(data: bytes) -> bool:
    return all(byte < 128 for byte in data)
