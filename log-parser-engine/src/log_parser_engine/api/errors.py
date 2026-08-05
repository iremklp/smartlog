from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from log_parser_engine.exceptions import (
    AnalysisComparisonError,
    AnalysisConcurrencyLimitError,
    AnalysisEventLimitError,
    AnalysisFieldResolutionError,
    AnalysisGroupLimitError,
    AnalysisInsufficientDataError,
    AnalysisNumericValueError,
    AnalysisRequestError,
    AnalysisSampleLimitError,
    AnalysisTimelineLimitError,
    ArchiveBombError,
    ArchiveEntrySelectionError,
    ArchiveEntryTooLargeError,
    ArchiveNotAllowedError,
    BinaryContentError,
    DuplicateEventError,
    EmptyContentError,
    EventAggregationError,
    EventIdCollisionError,
    EventPaginationError,
    EventQueryError,
    EventStoreCapacityError,
    IngestionError,
    InputTooLargeError,
    NestedArchiveError,
    NoParserFoundError,
    UnsupportedLogFormatError,
)
from log_parser_engine.exceptions.parser_registry import ParserNotFoundError

from .request_id import get_request_id, new_request_id
from .schemas import ApiErrorDetail, ApiErrorResponse

_ANALYSIS_PATHS = frozenset(
    {
        "/analysis",
        "/analysis/compare",
        "/api/v1/analysis",
        "/api/v1/analysis/compare",
    }
)


class ApiResponseTooLargeError(Exception):
    """Raised when a response payload estimate exceeds configured limits."""


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(InputTooLargeError, _input_too_large_handler)
    app.add_exception_handler(EmptyContentError, _empty_content_handler)
    app.add_exception_handler(IngestionError, _ingestion_error_handler)
    app.add_exception_handler(ArchiveNotAllowedError, _archive_rejected_handler)
    app.add_exception_handler(
        ArchiveEntrySelectionError,
        _archive_rejected_handler,
    )
    app.add_exception_handler(
        ArchiveEntryTooLargeError,
        _archive_too_large_handler,
    )
    app.add_exception_handler(ArchiveBombError, _archive_too_large_handler)
    app.add_exception_handler(NestedArchiveError, _archive_rejected_handler)
    app.add_exception_handler(BinaryContentError, _binary_content_handler)
    app.add_exception_handler(ParserNotFoundError, _parser_not_found_handler)
    app.add_exception_handler(NoParserFoundError, _parser_detection_handler)
    app.add_exception_handler(
        UnsupportedLogFormatError,
        _parser_detection_handler,
    )
    app.add_exception_handler(DuplicateEventError, _conflict_handler)
    app.add_exception_handler(EventIdCollisionError, _conflict_handler)
    app.add_exception_handler(EventStoreCapacityError, _capacity_handler)
    app.add_exception_handler(EventQueryError, _query_handler)
    app.add_exception_handler(EventPaginationError, _query_handler)
    app.add_exception_handler(EventAggregationError, _query_handler)
    app.add_exception_handler(ApiResponseTooLargeError, _response_too_large_handler)
    app.add_exception_handler(AnalysisEventLimitError, _analysis_limit_handler)
    app.add_exception_handler(
        AnalysisConcurrencyLimitError,
        _analysis_concurrency_handler,
    )
    app.add_exception_handler(AnalysisRequestError, _analysis_request_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(Exception, _internal_error_handler)


async def _input_too_large_handler(_: Request, __: Exception) -> JSONResponse:
    return _api_error_response(
        status_code=413,
        code="REQUEST_ENTITY_TOO_LARGE",
        message="input exceeds the configured size limit",
    )


async def _empty_content_handler(_: Request, __: Exception) -> JSONResponse:
    return _api_error_response(
        status_code=400,
        code="EMPTY_CONTENT",
        message="uploaded file is empty",
    )


async def _ingestion_error_handler(_: Request, __: Exception) -> JSONResponse:
    return _api_error_response(
        status_code=400,
        code="INGESTION_FAILED",
        message="uploaded file could not be ingested",
    )


async def _archive_rejected_handler(_: Request, __: Exception) -> JSONResponse:
    return _api_error_response(
        status_code=400,
        code="ARCHIVE_CONTENT_REJECTED",
        message="archive content is not allowed",
    )


async def _archive_too_large_handler(_: Request, __: Exception) -> JSONResponse:
    return _api_error_response(
        status_code=413,
        code="ARCHIVE_CONTENT_TOO_LARGE",
        message="archive content exceeds configured limits",
    )


async def _binary_content_handler(_: Request, __: Exception) -> JSONResponse:
    return _api_error_response(
        status_code=400,
        code="BINARY_CONTENT_NOT_ALLOWED",
        message="uploaded file could not be ingested",
    )


async def _parser_not_found_handler(_: Request, __: Exception) -> JSONResponse:
    return _api_error_response(
        status_code=404,
        code="PARSER_NOT_FOUND",
        message="requested parser was not found",
    )


async def _parser_detection_handler(_: Request, __: Exception) -> JSONResponse:
    return _api_error_response(
        status_code=400,
        code="PARSER_DETECTION_FAILED",
        message="no parser matched the input",
    )


async def _conflict_handler(_: Request, __: Exception) -> JSONResponse:
    return _api_error_response(
        status_code=409,
        code="EVENT_CONFLICT",
        message="event write conflicts with existing data",
    )


async def _capacity_handler(_: Request, __: Exception) -> JSONResponse:
    return _api_error_response(
        status_code=409,
        code="STORE_CAPACITY_EXCEEDED",
        message="store capacity limits were reached",
    )


async def _query_handler(_: Request, __: Exception) -> JSONResponse:
    return _api_error_response(
        status_code=400,
        code="QUERY_REQUEST_INVALID",
        message="query request could not be executed",
    )


async def _response_too_large_handler(_: Request, __: Exception) -> JSONResponse:
    return _api_error_response(
        status_code=413,
        code="RESPONSE_LIMIT_EXCEEDED",
        message="response exceeds configured size limit",
    )


async def _analysis_limit_handler(_: Request, exc: Exception) -> JSONResponse:
    details: dict[str, object] = {}
    if isinstance(exc, AnalysisEventLimitError):
        details = {"event_count": exc.count, "limit": exc.limit}
    return _api_error_response(
        status_code=413,
        code="ANALYSIS_EVENT_LIMIT_EXCEEDED",
        message="Analysis dataset exceeds limit.",
        details=details,
    )


async def _analysis_concurrency_handler(
    _: Request,
    exc: Exception,
) -> JSONResponse:
    details: dict[str, object] = {}
    if isinstance(exc, AnalysisConcurrencyLimitError):
        details = {"limit": exc.limit}
    return _api_error_response(
        status_code=429,
        code="ANALYSIS_CONCURRENCY_LIMIT_REACHED",
        message="Analysis capacity is temporarily exhausted.",
        details=details,
        headers={"Retry-After": "1"},
    )


async def _analysis_request_handler(_: Request, exc: Exception) -> JSONResponse:
    code = _analysis_request_error_code(exc)
    details: dict[str, object] = {}
    if isinstance(exc, AnalysisGroupLimitError):
        details = {
            "field": exc.field,
            "group_count": exc.count,
            "limit": exc.limit,
        }
    return _api_error_response(
        status_code=400,
        code=code,
        message="Analysis request could not be executed.",
        details=details,
    )


async def _validation_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        raise exc
    fields = tuple(
        ".".join(str(part) for part in error.get("loc", ()) if part != "body")
        for error in exc.errors()
    )
    safe_fields = tuple(dict.fromkeys(field for field in fields if field))[:20]
    code = (
        "ANALYSIS_REQUEST_VALIDATION_FAILED"
        if request.url.path in _ANALYSIS_PATHS
        else "REQUEST_VALIDATION_FAILED"
    )
    return _api_error_response(
        status_code=422,
        code=code,
        message="request validation failed",
        details={"fields": list(safe_fields)},
    )


async def _http_exception_handler(
    _: Request,
    exc: Exception,
) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):
        raise exc
    message = "request failed"
    if isinstance(exc.detail, str):
        candidate = exc.detail.strip()
        if candidate:
            message = candidate
    return _api_error_response(
        status_code=exc.status_code,
        code=f"HTTP_{exc.status_code}",
        message=message,
        headers=exc.headers,
    )


async def _internal_error_handler(_: Request, __: Exception) -> JSONResponse:
    return _api_error_response(
        status_code=500,
        code="INTERNAL_SERVER_ERROR",
        message="internal server error",
    )


def _analysis_request_error_code(exc: Exception) -> str:
    if isinstance(exc, AnalysisGroupLimitError):
        return "ANALYSIS_GROUP_LIMIT_EXCEEDED"
    if isinstance(exc, AnalysisTimelineLimitError):
        return "ANALYSIS_TIMELINE_LIMIT_EXCEEDED"
    if isinstance(exc, AnalysisSampleLimitError):
        return "ANALYSIS_SAMPLE_LIMIT_EXCEEDED"
    if isinstance(exc, AnalysisNumericValueError):
        return "ANALYSIS_NUMERIC_VALUE_INVALID"
    if isinstance(exc, AnalysisFieldResolutionError):
        return "ANALYSIS_FIELD_INVALID"
    if isinstance(exc, AnalysisComparisonError):
        return "ANALYSIS_COMPARISON_INVALID"
    if isinstance(exc, AnalysisInsufficientDataError):
        return "ANALYSIS_INSUFFICIENT_DATA"
    return "ANALYSIS_REQUEST_INVALID"


def _api_error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, object] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    request_id = get_request_id() or new_request_id()
    payload = ApiErrorResponse(
        detail=message,
        error=ApiErrorDetail(
            code=code,
            message=message,
            request_id=request_id,
            timestamp=datetime.now(timezone.utc),
            details=details or {},
        ),
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
        headers=headers,
    )