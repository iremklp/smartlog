from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from log_parser_engine.application import ApplicationContainer, ApplicationOptions, LogAnalysisApplicationService

from .errors import register_exception_handlers
from .middleware import request_id_middleware
from .routes import router


def _resolve_cors_origins() -> tuple[str, ...]:
    configured = os.getenv("LOG_PARSER_CORS_ORIGINS", "").strip()
    if configured:
        origins = tuple(item.strip() for item in configured.split(",") if item.strip())
        if origins:
            return origins
    return (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )


def create_app(
    *,
    container: ApplicationContainer | None = None,
    options: ApplicationOptions | None = None,
) -> FastAPI:
    resolved_container = container or ApplicationContainer.build(options=options)
    service = LogAnalysisApplicationService(resolved_container)

    app = FastAPI(title=resolved_container.options.name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(_resolve_cors_origins()),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    app.state.container = resolved_container
    app.state.service = service
    app.middleware("http")(request_id_middleware)
    app.include_router(router)
    register_exception_handlers(app)
    return app