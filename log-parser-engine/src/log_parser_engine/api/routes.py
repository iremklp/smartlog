from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from log_parser_engine.application import (
    AnalyzeEventsCommand,
    ApplicationHealth,
    ApplicationRuntimeStatistics,
    CompareEventsCommand,
    LogAnalysisApplicationService,
)
from log_parser_engine.core import ParserContext
from log_parser_engine.exceptions import EmptyContentError
from log_parser_engine.models import IngestionResult

from .dependencies import get_service
from .response_models import (
    AggregationApiResponse,
    BatchParseResultApiResponse,
    BatchWriteResultApiResponse,
    EventWriteResultApiResponse,
    ParseResultApiResponse,
    ParserRegistrationApiResponse,
    PipelineResultApiResponse,
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
    result = service.parse_text(
        payload.raw_log,
        context=payload.context,
        options=payload.options,
    )
    return PipelineResultApiResponse.from_domain(result)


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

    source_label = source_name or file.filename
    ingestion = service.ingest_bytes(payload, source_name=source_label)
    context = ParserContext(
        source_name=source_label,
        file_path=file.filename,
        content_type=file.content_type,
        attributes=ingestion.parser_context_attributes,
    )

    if batch_mode:
        if store_result:
            return BatchWriteResultApiResponse.from_domain(
                service.batch_parse_and_store_text(ingestion.text, context=context)
            )
        return BatchParseResultApiResponse.from_domain(
            service.batch_parse_text(ingestion.text, context=context)
        )

    if parser_name:
        parse_result = service.parse_with_parser(
            parser_name,
            ingestion.text,
            context=context,
            allow_disabled_parser=allow_disabled_parser,
        )
        if store_result:
            if not parse_result.events:
                raise HTTPException(
                    status_code=400,
                    detail="parser did not produce an event to store",
                )
            return EventWriteResultApiResponse.from_domain(
                service.add_event(parse_result.events[0])
            )
        return ParseResultApiResponse.from_domain(parse_result)

    if store_result:
        try:
            return EventWriteResultApiResponse.from_domain(
                service.parse_and_store_text(ingestion.text, context=context)
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PipelineResultApiResponse.from_domain(
        service.parse_text(ingestion.text, context=context)
    )


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
        return EventWriteResultApiResponse.from_domain(service.parse_and_store_text(
            payload.raw_log,
            context=payload.context,
            options=payload.options,
        ))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
    return ParseResultApiResponse.from_domain(service.parse_with_parser(
        parser_name,
        payload.raw_log,
        context=payload.context,
        allow_disabled_parser=payload.allow_disabled_parser,
    ))


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
    return BatchParseResultApiResponse.from_domain(service.batch_parse_text(
        payload.text,
        context=payload.context,
        options=payload.options,
    ))


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
    return BatchWriteResultApiResponse.from_domain(service.batch_parse_and_store_text(
        payload.text,
        context=payload.context,
        options=payload.options,
    ))


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
    return {"deleted": service.delete_event(event_id)}


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
    return QueryApiResponse.from_domain(service.query_events(payload.query))


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
    result = service.aggregate_events(payload.request, base_query=payload.base_query)
    if result is None:
        return None
    return AggregationApiResponse.from_domain(result)


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
