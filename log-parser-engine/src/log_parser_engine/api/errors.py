from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from log_parser_engine.exceptions import (
    DuplicateEventError,
    EventIdCollisionError,
    EventStoreCapacityError,
)
from log_parser_engine.exceptions.parser_registry import ParserNotFoundError


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ParserNotFoundError, _not_found_handler)
    app.add_exception_handler(DuplicateEventError, _conflict_handler)
    app.add_exception_handler(EventIdCollisionError, _conflict_handler)
    app.add_exception_handler(EventStoreCapacityError, _conflict_handler)


async def _not_found_handler(_: Request, exc: ParserNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def _conflict_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})