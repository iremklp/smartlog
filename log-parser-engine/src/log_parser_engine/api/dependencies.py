from __future__ import annotations

from fastapi import Request

from log_parser_engine.application import ApplicationContainer, LogAnalysisApplicationService


def get_container(request: Request) -> ApplicationContainer:
    container = request.app.state.container
    if not isinstance(container, ApplicationContainer):
        raise RuntimeError("application container is not configured")
    return container


def get_service(request: Request) -> LogAnalysisApplicationService:
    service = request.app.state.service
    if not isinstance(service, LogAnalysisApplicationService):
        raise RuntimeError("application service is not configured")
    return service