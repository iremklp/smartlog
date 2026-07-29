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
from log_parser_engine.models import (
    BatchParseResult,
    BatchWriteResult,
    EventAggregationResult,
    EventQueryResult,
    EventStoreStatistics,
    EventWriteResult,
    IngestionResult,
    ParseResult,
    ParserRegistration,
    PipelineResult,
    StoredEvent,
)

from .dependencies import get_service
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


@router.get("/health")
def health(
    service: LogAnalysisApplicationService = Depends(get_service),
) -> ApplicationHealth:
    return service.health()


@router.get("/runtime/statistics")
def runtime_statistics(
    service: LogAnalysisApplicationService = Depends(get_service),
) -> ApplicationRuntimeStatistics:
    return service.runtime_statistics()


@router.get("/store/statistics")
def store_statistics(
    service: LogAnalysisApplicationService = Depends(get_service),
) -> EventStoreStatistics:
    return service.store_statistics()


@router.get("/parsers")
def list_parsers(
    service: LogAnalysisApplicationService = Depends(get_service),
) -> tuple[ParserRegistration, ...]:
    return service.list_parsers()


@router.post(
    "/analysis",
    tags=["Analysis"],
    include_in_schema=False,
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
    include_in_schema=False,
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


@router.post("/ingest/text")
def ingest_text(
    payload: IngestTextRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> IngestionResult:
    return service.ingest_text(payload.text, source_name=payload.source_name)


@router.post("/parse")
def parse_text(
    payload: ParseRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> PipelineResult:
    return service.parse_text(
        payload.raw_log,
        context=payload.context,
        options=payload.options,
    )


@router.post("/parse/file")
async def parse_file(
    file: UploadFile = File(...),
    source_name: str | None = Form(default=None),
    parser_name: str | None = Form(default=None),
    store_result: bool = Form(default=False),
    batch_mode: bool = Form(default=False),
    allow_disabled_parser: bool = Form(default=False),
    service: LogAnalysisApplicationService = Depends(get_service),
) -> (
    PipelineResult
    | ParseResult
    | BatchParseResult
    | EventWriteResult
    | BatchWriteResult
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
            return service.batch_parse_and_store_text(ingestion.text, context=context)
        return service.batch_parse_text(ingestion.text, context=context)

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
            return service.add_event(parse_result.events[0])
        return parse_result

    if store_result:
        try:
            return service.parse_and_store_text(ingestion.text, context=context)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return service.parse_text(ingestion.text, context=context)


@router.post("/parse/store")
def parse_and_store_text(
    payload: ParseRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> EventWriteResult:
    try:
        return service.parse_and_store_text(
            payload.raw_log,
            context=payload.context,
            options=payload.options,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/parse/{parser_name}")
def parse_with_parser(
    parser_name: str,
    payload: ParseWithParserRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> ParseResult:
    return service.parse_with_parser(
        parser_name,
        payload.raw_log,
        context=payload.context,
        allow_disabled_parser=payload.allow_disabled_parser,
    )


@router.post("/batch/parse")
def batch_parse_text(
    payload: BatchParseRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> BatchParseResult:
    return service.batch_parse_text(
        payload.text,
        context=payload.context,
        options=payload.options,
    )


@router.post("/batch/parse/store")
def batch_parse_and_store_text(
    payload: BatchParseRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> BatchWriteResult:
    return service.batch_parse_and_store_text(
        payload.text,
        context=payload.context,
        options=payload.options,
    )


@router.post("/events")
def add_event(
    payload: AddEventRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> EventWriteResult:
    return service.add_event(payload.event, options=payload.options)


@router.post("/events/batch")
def add_many_events(
    payload: AddManyEventsRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> BatchWriteResult:
    return service.add_many_events(payload.events, options=payload.options)


@router.get("/events/{event_id}")
def get_event(
    event_id: str,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> StoredEvent:
    event = service.get_event(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="event not found")
    return event


@router.delete("/events/{event_id}")
def delete_event(
    event_id: str,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> dict[str, bool]:
    return {"deleted": service.delete_event(event_id)}


@router.post("/query")
def query_events(
    payload: QueryRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> EventQueryResult:
    return service.query_events(payload.query)


@router.post("/aggregate")
def aggregate_events(
    payload: AggregateRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> EventAggregationResult | None:
    return service.aggregate_events(payload.request, base_query=payload.base_query)
