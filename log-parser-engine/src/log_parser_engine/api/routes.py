from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from log_parser_engine.application import (
    AnalyzeEventsCommand,
    ApplicationHealth,
    ApplicationRuntimeStatistics,
    CompareEventsCommand,
    LogAnalysisApplicationService,
    ParseBytesCommand,
    ParseTextCommand,
)
from log_parser_engine.exceptions import EmptyContentError
from log_parser_engine.models import (
    BatchParseResult,
    BatchWriteResult,
    EventWriteResult,
    IngestionResult,
    ParseResult,
    PipelineResult,
)

from .dependencies import get_service
from .errors import ApiResponseTooLargeError
from .response_models import (
    AggregationApiResponse,
    BatchParseResultApiResponse,
    BatchWriteResultApiResponse,
    EventWriteResultApiResponse,
    ParseResultApiResponse,
    ParserRegistrationApiResponse,
    PipelineResultApiResponse,
    PublicApiConfigApiResponse,
    QueryApiResponse,
    StoredEventDetailApiResponse,
    StoreStatisticsApiResponse,
)
from .schemas import (
    AddEventRequest,
    AddManyEventsRequest,
    AggregateRequest,
    AnalysisApiErrorResponse,
    AnalysisApiRequest,
    AnalysisApiResponse,
    BatchParseRequest,
    ComparisonApiRequest,
    ComparisonApiResponse,
    IngestTextRequest,
    ParseRequest,
    ParseWithParserRequest,
    QueryRequest,
    StoreClearRequest,
)
from .uploads import read_bounded_upload

router = APIRouter()


@router.get("/api/v1/health", summary="Get API health")
def health(
    service: LogAnalysisApplicationService = Depends(get_service),
) -> ApplicationHealth:
    return service.health()


@router.get(
    "/health",
    deprecated=True,
)
def health_legacy(
    service: LogAnalysisApplicationService = Depends(get_service),
) -> ApplicationHealth:
    return health(service)


@router.get("/api/v1/runtime/statistics", summary="Get runtime statistics")
def runtime_statistics(
    service: LogAnalysisApplicationService = Depends(get_service),
) -> ApplicationRuntimeStatistics:
    return service.runtime_statistics()


@router.get(
    "/runtime/statistics",
    deprecated=True,
)
def runtime_statistics_legacy(
    service: LogAnalysisApplicationService = Depends(get_service),
) -> ApplicationRuntimeStatistics:
    return runtime_statistics(service)


@router.get(
    "/api/v1/store/statistics",
    response_model=StoreStatisticsApiResponse,
    summary="Get store statistics",
)
def store_statistics(
    service: LogAnalysisApplicationService = Depends(get_service),
) -> StoreStatisticsApiResponse:
    return StoreStatisticsApiResponse.from_domain(service.store_statistics())


@router.get(
    "/store/statistics",
    deprecated=True,
    response_model=StoreStatisticsApiResponse,
)
def store_statistics_legacy(
    service: LogAnalysisApplicationService = Depends(get_service),
) -> StoreStatisticsApiResponse:
    return store_statistics(service)


@router.get(
    "/api/v1/parsers",
    response_model=tuple[ParserRegistrationApiResponse, ...],
    summary="List parser registrations",
)
def list_parsers(
    service: LogAnalysisApplicationService = Depends(get_service),
) -> tuple[ParserRegistrationApiResponse, ...]:
    return tuple(
        ParserRegistrationApiResponse.from_domain(parser)
        for parser in service.list_parsers()
    )


@router.get(
    "/parsers",
    deprecated=True,
    response_model=tuple[ParserRegistrationApiResponse, ...],
)
def list_parsers_legacy(
    service: LogAnalysisApplicationService = Depends(get_service),
) -> tuple[ParserRegistrationApiResponse, ...]:
    return list_parsers(service)


@router.get(
    "/api/v1/config",
    response_model=PublicApiConfigApiResponse,
    summary="Get safe public API config",
)
def public_config(
    service: LogAnalysisApplicationService = Depends(get_service),
) -> PublicApiConfigApiResponse:
    config = service.public_config()
    return PublicApiConfigApiResponse.model_validate(config.model_dump(mode="json"))


@router.get(
    "/config",
    deprecated=True,
    response_model=PublicApiConfigApiResponse,
)
def public_config_legacy(
    service: LogAnalysisApplicationService = Depends(get_service),
) -> PublicApiConfigApiResponse:
    return public_config(service)


@router.post(
    "/analysis",
    tags=["Analysis"],
    deprecated=True,
    response_model=AnalysisApiResponse,
)
@router.post(
    "/api/v1/analysis",
    tags=["Analysis"],
    response_model=AnalysisApiResponse,
    responses={
        400: {"model": AnalysisApiErrorResponse},
        413: {"model": AnalysisApiErrorResponse},
        422: {"model": AnalysisApiErrorResponse},
    },
    summary="Analyze stored events",
)
def analyze_events(
    payload: AnalysisApiRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> AnalysisApiResponse:
    command = AnalyzeEventsCommand(request=payload)
    result = service.analyze_events(command).result
    return AnalysisApiResponse.from_domain(
        result,
        options=service.container.options.analysis_options,
    )


@router.post(
    "/analysis/compare",
    tags=["Analysis"],
    deprecated=True,
    response_model=ComparisonApiResponse,
)
@router.post(
    "/api/v1/analysis/compare",
    tags=["Analysis"],
    response_model=ComparisonApiResponse,
    responses={
        400: {"model": AnalysisApiErrorResponse},
        413: {"model": AnalysisApiErrorResponse},
        422: {"model": AnalysisApiErrorResponse},
    },
    summary="Compare two stored-event scopes",
)
def compare_events(
    payload: ComparisonApiRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> ComparisonApiResponse:
    command = CompareEventsCommand(request=payload)
    result = service.compare_events(command).result
    return ComparisonApiResponse.from_domain(
        result,
        options=service.container.options.analysis_options,
    )


@router.post("/api/v1/ingest/text", summary="Ingest raw text")
def ingest_text(
    payload: IngestTextRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> IngestionResult:
    return service.ingest_text(payload.text, source_name=payload.source_name)


@router.post(
    "/ingest/text",
    deprecated=True,
)
def ingest_text_legacy(
    payload: IngestTextRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> IngestionResult:
    return ingest_text(payload, service)


@router.post(
    "/api/v1/parse",
    response_model=PipelineResultApiResponse,
    summary="Parse text",
)
def parse_text(
    payload: ParseRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> PipelineResultApiResponse:
    command = ParseTextCommand(
        raw_log=payload.raw_log,
        context=payload.context,
        options=payload.options,
    )
    response = service.execute_parse_text(command)
    if isinstance(response.result, PipelineResult):
        return PipelineResultApiResponse.from_domain(response.result)
    raise HTTPException(status_code=500, detail="unexpected parse response")


@router.post(
    "/parse",
    deprecated=True,
    response_model=PipelineResultApiResponse,
)
def parse_text_legacy(
    payload: ParseRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> PipelineResultApiResponse:
    return parse_text(payload, service)


@router.post(
    "/api/v1/parse/file",
    response_model=(
        PipelineResultApiResponse
        | ParseResultApiResponse
        | BatchParseResultApiResponse
        | EventWriteResultApiResponse
        | BatchWriteResultApiResponse
    ),
    summary="Parse uploaded file",
)
async def parse_file(
    file: UploadFile = File(...),
    source_name: str | None = Form(default=None),
    parser_name: str | None = Form(default=None),
    store_result: bool = Form(default=False),
    batch_mode: bool = Form(default=False),
    allow_disabled_parser: bool = Form(default=False),
    service: LogAnalysisApplicationService = Depends(get_service),
) -> (
    PipelineResultApiResponse
    | ParseResultApiResponse
    | BatchParseResultApiResponse
    | EventWriteResultApiResponse
    | BatchWriteResultApiResponse
):
    try:
        payload = await read_bounded_upload(
            file,
            max_bytes=service.container.options.max_upload_bytes,
        )
    except EmptyContentError as exc:
        raise HTTPException(
            status_code=400,
            detail="uploaded file is empty",
        ) from exc

    command = ParseBytesCommand(
        data=payload,
        source_name=source_name,
        file_name=file.filename,
        content_type=file.content_type,
        parser_name=parser_name,
        store_result=store_result,
        batch_mode=batch_mode,
        allow_disabled_parser=allow_disabled_parser,
    )
    try:
        response = service.execute_parse_bytes(command)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_parse_api_response(response.result)


@router.post(
    "/parse/file",
    deprecated=True,
    response_model=(
        PipelineResultApiResponse
        | ParseResultApiResponse
        | BatchParseResultApiResponse
        | EventWriteResultApiResponse
        | BatchWriteResultApiResponse
    ),
)
async def parse_file_legacy(
    file: UploadFile = File(...),
    source_name: str | None = Form(default=None),
    parser_name: str | None = Form(default=None),
    store_result: bool = Form(default=False),
    batch_mode: bool = Form(default=False),
    allow_disabled_parser: bool = Form(default=False),
    service: LogAnalysisApplicationService = Depends(get_service),
) -> (
    PipelineResultApiResponse
    | ParseResultApiResponse
    | BatchParseResultApiResponse
    | EventWriteResultApiResponse
    | BatchWriteResultApiResponse
):
    return await parse_file(
        file=file,
        source_name=source_name,
        parser_name=parser_name,
        store_result=store_result,
        batch_mode=batch_mode,
        allow_disabled_parser=allow_disabled_parser,
        service=service,
    )


@router.post(
    "/api/v1/parse/store",
    response_model=EventWriteResultApiResponse,
    summary="Parse and store text",
)
def parse_and_store_text(
    payload: ParseRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> EventWriteResultApiResponse:
    try:
        response = service.execute_parse_text(
            ParseTextCommand(
                raw_log=payload.raw_log,
                context=payload.context,
                options=payload.options,
                store_result=True,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if isinstance(response.result, EventWriteResult):
        return EventWriteResultApiResponse.from_domain(response.result)
    raise HTTPException(status_code=500, detail="unexpected parse response")


@router.post(
    "/parse/store",
    deprecated=True,
    response_model=EventWriteResultApiResponse,
)
def parse_and_store_text_legacy(
    payload: ParseRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> EventWriteResultApiResponse:
    return parse_and_store_text(payload, service)


@router.post(
    "/api/v1/parse/{parser_name}",
    response_model=ParseResultApiResponse,
    summary="Parse with explicit parser",
)
def parse_with_parser(
    parser_name: str,
    payload: ParseWithParserRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> ParseResultApiResponse:
    response = service.execute_parse_text(
        ParseTextCommand(
            raw_log=payload.raw_log,
            context=payload.context,
            parser_name=parser_name,
            allow_disabled_parser=payload.allow_disabled_parser,
        )
    )
    if isinstance(response.result, ParseResult):
        return ParseResultApiResponse.from_domain(response.result)
    raise HTTPException(status_code=500, detail="unexpected parse response")


@router.post(
    "/parse/{parser_name}",
    deprecated=True,
    response_model=ParseResultApiResponse,
)
def parse_with_parser_legacy(
    parser_name: str,
    payload: ParseWithParserRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> ParseResultApiResponse:
    return parse_with_parser(parser_name, payload, service)


@router.post(
    "/api/v1/batch/parse",
    response_model=BatchParseResultApiResponse,
    summary="Batch parse text",
)
def batch_parse_text(
    payload: BatchParseRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> BatchParseResultApiResponse:
    response = service.execute_parse_text(
        ParseTextCommand(
            raw_log=payload.text,
            context=payload.context,
            batch_mode=True,
        )
    )
    if isinstance(response.result, BatchParseResult):
        return BatchParseResultApiResponse.from_domain(response.result)
    raise HTTPException(status_code=500, detail="unexpected parse response")


@router.post(
    "/batch/parse",
    deprecated=True,
    response_model=BatchParseResultApiResponse,
)
def batch_parse_text_legacy(
    payload: BatchParseRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> BatchParseResultApiResponse:
    return batch_parse_text(payload, service)


@router.post(
    "/api/v1/batch/parse/store",
    response_model=BatchWriteResultApiResponse,
    summary="Batch parse and store text",
)
def batch_parse_and_store_text(
    payload: BatchParseRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> BatchWriteResultApiResponse:
    response = service.execute_parse_text(
        ParseTextCommand(
            raw_log=payload.text,
            context=payload.context,
            batch_mode=True,
            store_result=True,
        )
    )
    if isinstance(response.result, BatchWriteResult):
        return BatchWriteResultApiResponse.from_domain(response.result)
    raise HTTPException(status_code=500, detail="unexpected parse response")


@router.post(
    "/batch/parse/store",
    deprecated=True,
    response_model=BatchWriteResultApiResponse,
)
def batch_parse_and_store_text_legacy(
    payload: BatchParseRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> BatchWriteResultApiResponse:
    return batch_parse_and_store_text(payload, service)


@router.post(
    "/api/v1/events",
    response_model=EventWriteResultApiResponse,
    summary="Add one event",
)
def add_event(
    payload: AddEventRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> EventWriteResultApiResponse:
    _require_capability(
        service.container.options.allow_public_event_write,
        "direct event write is disabled",
    )
    _validate_metadata(payload.options.metadata, service)
    return EventWriteResultApiResponse.from_domain(
        service.add_event(payload.event, options=payload.options)
    )


@router.post(
    "/events",
    deprecated=True,
    response_model=EventWriteResultApiResponse,
)
def add_event_legacy(
    payload: AddEventRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> EventWriteResultApiResponse:
    return add_event(payload, service)


@router.post(
    "/api/v1/events/batch",
    response_model=BatchWriteResultApiResponse,
    summary="Add many events",
)
def add_many_events(
    payload: AddManyEventsRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> BatchWriteResultApiResponse:
    _require_capability(
        service.container.options.allow_public_event_write,
        "direct event write is disabled",
    )
    _validate_metadata(payload.options.metadata, service)
    return BatchWriteResultApiResponse.from_domain(
        service.add_many_events(payload.events, options=payload.options)
    )


@router.post(
    "/events/batch",
    deprecated=True,
    response_model=BatchWriteResultApiResponse,
)
def add_many_events_legacy(
    payload: AddManyEventsRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> BatchWriteResultApiResponse:
    return add_many_events(payload, service)


@router.get(
    "/api/v1/events/{event_id}",
    response_model=StoredEventDetailApiResponse,
    summary="Get event detail",
)
def get_event(
    event_id: str,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> StoredEventDetailApiResponse:
    event = service.get_event(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="event not found")
    return StoredEventDetailApiResponse.from_domain(event)


@router.get(
    "/events/{event_id}",
    deprecated=True,
    response_model=StoredEventDetailApiResponse,
)
def get_event_legacy(
    event_id: str,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> StoredEventDetailApiResponse:
    return get_event(event_id, service)


@router.delete("/api/v1/events/{event_id}", summary="Delete event by id")
def delete_event(
    event_id: str,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> dict[str, bool]:
    _require_capability(
        service.container.options.allow_public_event_delete,
        "event deletion is disabled",
    )
    return {"deleted": service.delete_event(event_id)}


@router.post(
    "/api/v1/store/clear",
    summary="Clear all stored events",
)
def clear_store(
    payload: StoreClearRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> dict[str, int]:
    _require_capability(
        service.container.options.allow_public_store_clear,
        "store clear is disabled",
    )
    expected = service.container.options.store_clear_confirmation
    if payload.confirmation.strip() != expected:
        raise HTTPException(
            status_code=400,
            detail="store clear confirmation does not match",
        )
    return {"cleared": service.clear_events()}


@router.post(
    "/store/clear",
    deprecated=True,
)
def clear_store_legacy(
    payload: StoreClearRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> dict[str, int]:
    return clear_store(payload, service)


@router.delete(
    "/events/{event_id}",
    deprecated=True,
)
def delete_event_legacy(
    event_id: str,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> dict[str, bool]:
    return delete_event(event_id, service)


@router.post(
    "/api/v1/query",
    response_model=QueryApiResponse,
    summary="Query events",
)
def query_events(
    payload: QueryRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> QueryApiResponse:
    _validate_query_request(payload.query, service)
    response = QueryApiResponse.from_domain(service.query_events(payload.query))
    _enforce_response_size_limit(response, service)
    return response


@router.post(
    "/query",
    deprecated=True,
    response_model=QueryApiResponse,
)
def query_events_legacy(
    payload: QueryRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> QueryApiResponse:
    return query_events(payload, service)


@router.post(
    "/api/v1/aggregate",
    response_model=AggregationApiResponse | None,
    summary="Aggregate events",
)
def aggregate_events(
    payload: AggregateRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> AggregationApiResponse | None:
    _validate_aggregation_limit(payload.request.limit, service)
    if payload.base_query is not None:
        _validate_query_request(payload.base_query, service)
    result = service.aggregate_events(payload.request, base_query=payload.base_query)
    if result is None:
        return None
    response = AggregationApiResponse.from_domain(result)
    _enforce_response_size_limit(response, service)
    return response


@router.post(
    "/aggregate",
    deprecated=True,
    response_model=AggregationApiResponse | None,
)
def aggregate_events_legacy(
    payload: AggregateRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> AggregationApiResponse | None:
    return aggregate_events(payload, service)


def _to_parse_api_response(
    result: (
        PipelineResult
        | ParseResult
        | BatchParseResult
        | EventWriteResult
        | BatchWriteResult
    ),
) -> (
    PipelineResultApiResponse
    | ParseResultApiResponse
    | BatchParseResultApiResponse
    | EventWriteResultApiResponse
    | BatchWriteResultApiResponse
):
    if isinstance(result, PipelineResult):
        return PipelineResultApiResponse.from_domain(result)
    if isinstance(result, ParseResult):
        return ParseResultApiResponse.from_domain(result)
    if isinstance(result, BatchParseResult):
        return BatchParseResultApiResponse.from_domain(result)
    if isinstance(result, EventWriteResult):
        return EventWriteResultApiResponse.from_domain(result)
    if isinstance(result, BatchWriteResult):
        return BatchWriteResultApiResponse.from_domain(result)
    raise HTTPException(status_code=500, detail="unexpected parse response")


def _require_capability(enabled: bool, message: str) -> None:
    if enabled:
        return
    raise HTTPException(status_code=403, detail=message)


def _validate_metadata(
    metadata: dict[str, Any],
    service: LogAnalysisApplicationService,
) -> None:
    options = service.container.options
    estimated_bytes = len(
        json.dumps(
            metadata,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    if estimated_bytes > options.max_metadata_bytes:
        raise HTTPException(
            status_code=413,
            detail="metadata exceeds configured size limit",
        )
    if _max_depth(metadata) > options.max_metadata_depth:
        raise HTTPException(
            status_code=400,
            detail="metadata exceeds configured depth limit",
        )


def _max_depth(value: object, depth: int = 1) -> int:
    if isinstance(value, dict):
        if not value:
            return depth
        return max(_max_depth(item, depth + 1) for item in value.values())
    if isinstance(value, list):
        if not value:
            return depth
        return max(_max_depth(item, depth + 1) for item in value)
    return depth


def _validate_query_request(
    query: Any,
    service: LogAnalysisApplicationService,
) -> None:
    options = service.container.options
    if (
        query.limit is not None
        and query.limit > options.event_store_options.max_page_size
    ):
        raise HTTPException(
            status_code=400,
            detail="query limit exceeds configured page size",
        )
    if len(query.facet_fields) > options.max_query_facet_fields:
        raise HTTPException(
            status_code=400,
            detail="facet field count exceeds configured limit",
        )
    if query.aggregation is not None:
        _validate_aggregation_limit(query.aggregation.limit, service)


def _validate_aggregation_limit(
    limit: int,
    service: LogAnalysisApplicationService,
) -> None:
    if limit <= service.container.options.max_aggregation_buckets:
        return
    raise HTTPException(
        status_code=400,
        detail="aggregation limit exceeds configured bucket limit",
    )


def _enforce_response_size_limit(
    payload: BaseModel,
    service: LogAnalysisApplicationService,
) -> None:
    estimated_bytes = len(payload.model_dump_json().encode("utf-8"))
    if estimated_bytes <= service.container.options.max_response_estimated_bytes:
        return
    raise ApiResponseTooLargeError()
