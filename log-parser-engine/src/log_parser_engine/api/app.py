from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from log_parser_engine.application import (
    ApplicationContainer,
    ApplicationOptions,
    LogAnalysisApplicationService,
)
from log_parser_engine.observability.logging import configure_structured_logging

from .errors import register_exception_handlers
from .middleware import (
    AnalysisRequestSizeLimitMiddleware,
    request_id_middleware,
)
from .routes import router
from .static_assets import SinglePageStaticFiles, resolve_frontend_dist


def _resolve_cors_origins(options: ApplicationOptions) -> tuple[str, ...]:
    configured = os.getenv("LOG_PARSER_CORS_ORIGINS", "").strip()
    if configured:
        origins = tuple(item.strip() for item in configured.split(",") if item.strip())
        if origins:
            validated = ApplicationOptions(cors_allowed_origins=origins)
            return validated.cors_allowed_origins
    return options.cors_allowed_origins


def _resolve_frontend_mode() -> str:
    mode = os.getenv("LOG_PARSER_FRONTEND_MODE", "auto").strip().lower()
    if mode in {"auto", "api-only", "require"}:
        return mode
    return "auto"


def create_app(
    *,
    container: ApplicationContainer | None = None,
    options: ApplicationOptions | None = None,
) -> FastAPI:
    configure_structured_logging()
    resolved_container = container or ApplicationContainer.build(options=options)
    service = LogAnalysisApplicationService(resolved_container)

    app = FastAPI(title=resolved_container.options.name)
    cors_origins = _resolve_cors_origins(resolved_container.options)
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(cors_origins),
            allow_credentials=False,
            allow_methods=["DELETE", "GET", "HEAD", "OPTIONS", "POST"],
            allow_headers=["Accept", "Content-Type", "X-Request-ID"],
            expose_headers=["X-Request-ID"],
        )
    app.add_middleware(
        AnalysisRequestSizeLimitMiddleware,
        max_body_bytes=resolved_container.options.max_analysis_request_body_bytes,
    )
    app.state.container = resolved_container
    app.state.service = service
    app.middleware("http")(request_id_middleware)
    app.include_router(router)

    frontend_mode = _resolve_frontend_mode()
    frontend_dist = resolve_frontend_dist(
        mode=frontend_mode,
        env_path=os.getenv("LOG_PARSER_FRONTEND_DIST"),
    )
    if frontend_dist is not None:
        # Use a dedicated mount class for SPA fallback while preserving API routes.
        app.mount(
            "/",
            SinglePageStaticFiles(directory=str(frontend_dist), html=True),
            name="frontend",
        )

    register_exception_handlers(app)
    return app
