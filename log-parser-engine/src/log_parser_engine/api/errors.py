from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

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
    DuplicateEventError,
    EventIdCollisionError,
    EventStoreCapacityError,
)
from log_parser_engine.exceptions.parser_registry import ParserNotFoundError

from .request_id import get_request_id, new_request_id
from .schemas import AnalysisApiErrorDetail, AnalysisApiErrorResponse

_ANALYSIS_PATHS = frozenset(
    {
        "/analysis",
        "/analysis/compare",
        "/api/v1/analysis",
        "/api/v1/analysis/compare",
    }
)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ParserNotFoundError, _not_found_handler)
    app.add_exception_handler(DuplicateEventError, _conflict_handler)
    app.add_exception_handler(EventIdCollisionError, _conflict_handler)
    app.add_exception_handler(EventStoreCapacityError, _conflict_handler)
    app.add_exception_handler(AnalysisEventLimitError, _analysis_limit_handler)
    app.add_exception_handler(
        AnalysisConcurrencyLimitError,
        _analysis_concurrency_handler,
    )
    app.add_exception_handler(AnalysisRequestError, _analysis_request_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)


async def _not_found_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def _conflict_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


async def _analysis_limit_handler(_: Request, exc: Exception) -> JSONResponse:
    details: dict[str, object] = {}
    if isinstance(exc, AnalysisEventLimitError):
        details = {"event_count": exc.count, "limit": exc.limit}
    return _analysis_error_response(
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
    return _analysis_error_response(
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
    return _analysis_error_response(
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
    if request.url.path not in _ANALYSIS_PATHS:
        return await request_validation_exception_handler(request, exc)
    fields = tuple(
        ".".join(str(part) for part in error.get("loc", ()) if part != "body")
        for error in exc.errors()
    )
    safe_fields = tuple(dict.fromkeys(field for field in fields if field))[:20]
    return _analysis_error_response(
        status_code=422,
        code="ANALYSIS_REQUEST_VALIDATION_FAILED",
        message="Analysis request validation failed.",
        details={"fields": list(safe_fields)},
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


def _analysis_error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    request_id = get_request_id() or new_request_id()
    error = AnalysisApiErrorResponse(
        detail=message,
        error=AnalysisApiErrorDetail(
            code=code,
            message=message,
            request_id=request_id,
            timestamp=datetime.now(timezone.utc),
            details=details or {},
        ),
    )
    return JSONResponse(
        status_code=status_code,
        content=error.model_dump(mode="json"),
        headers=headers,
    )
