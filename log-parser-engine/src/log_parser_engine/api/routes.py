from __future__ import annotations

from fastapi import APIRouter, Depends

from log_parser_engine.application import LogAnalysisApplicationService
from log_parser_engine.models import EventAggregationResult, EventQueryResult, EventWriteResult

from .dependencies import get_service
from .schemas import (
    AddEventRequest,
    AddManyEventsRequest,
    AggregateRequest,
    BatchParseRequest,
    IngestTextRequest,
    ParseRequest,
    ParseWithParserRequest,
    QueryRequest,
)

router = APIRouter()


@router.get("/health")
def health(service: LogAnalysisApplicationService = Depends(get_service)):
    return service.health()


@router.get("/runtime/statistics")
def runtime_statistics(service: LogAnalysisApplicationService = Depends(get_service)):
    return service.runtime_statistics()


@router.get("/parsers")
def list_parsers(service: LogAnalysisApplicationService = Depends(get_service)):
    return service.list_parsers()


@router.post("/ingest/text")
def ingest_text(
    payload: IngestTextRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
):
    return service.ingest_text(payload.text, source_name=payload.source_name)


@router.post("/parse")
def parse_text(
    payload: ParseRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
):
    return service.parse_text(payload.raw_log, context=payload.context, options=payload.options)


@router.post("/parse/{parser_name}")
def parse_with_parser(
    parser_name: str,
    payload: ParseWithParserRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
):
    return service.parse_with_parser(
        parser_name,
        payload.raw_log,
        context=payload.context,
        allow_disabled_parser=payload.allow_disabled_parser,
    )


@router.post("/parse/store")
def parse_and_store_text(
    payload: ParseRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
) -> EventWriteResult:
    return service.parse_and_store_text(
        payload.raw_log,
        context=payload.context,
        options=payload.options,
    )


@router.post("/batch/parse")
def batch_parse_text(
    payload: BatchParseRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
):
    return service.batch_parse_text(payload.text, context=payload.context, options=payload.options)


@router.post("/batch/parse/store")
def batch_parse_and_store_text(
    payload: BatchParseRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
):
    return service.batch_parse_and_store_text(
        payload.text,
        context=payload.context,
        options=payload.options,
    )


@router.post("/events")
def add_event(
    payload: AddEventRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
):
    return service.add_event(payload.event, options=payload.options)


@router.post("/events/batch")
def add_many_events(
    payload: AddManyEventsRequest,
    service: LogAnalysisApplicationService = Depends(get_service),
):
    return service.add_many_events(payload.events, options=payload.options)


@router.get("/events/{event_id}")
def get_event(event_id: str, service: LogAnalysisApplicationService = Depends(get_service)):
    return service.get_event(event_id)


@router.delete("/events/{event_id}")
def delete_event(event_id: str, service: LogAnalysisApplicationService = Depends(get_service)):
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