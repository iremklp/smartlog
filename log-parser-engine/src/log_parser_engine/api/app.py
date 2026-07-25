from __future__ import annotations

from fastapi import FastAPI

from log_parser_engine.application import ApplicationContainer, ApplicationOptions, LogAnalysisApplicationService

from .errors import register_exception_handlers
from .middleware import request_id_middleware
from .routes import router


def create_app(
    *,
    container: ApplicationContainer | None = None,
    options: ApplicationOptions | None = None,
) -> FastAPI:
    resolved_container = container or ApplicationContainer.build(options=options)
    service = LogAnalysisApplicationService(resolved_container)

    app = FastAPI(title=resolved_container.options.name)
    app.state.container = resolved_container
    app.state.service = service
    app.middleware("http")(request_id_middleware)
    app.include_router(router)
    register_exception_handlers(app)
    return app