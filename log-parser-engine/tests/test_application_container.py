from __future__ import annotations

from log_parser_engine.application import ApplicationContainer, ApplicationOptions
from log_parser_engine.core import ParserRegistry
from log_parser_engine.models import LogSourceType
from log_parser_engine.storage import InMemoryEventStore
from tests.helpers.fake_parser import FakeParser


def test_application_container_builds_with_injected_registry() -> None:
    parser = FakeParser("fake", source_type=LogSourceType.FILE)
    registry = ParserRegistry([parser])
    container = ApplicationContainer.build(
        options=ApplicationOptions(enable_builtin_parsers=False),
        registry=registry,
        store=InMemoryEventStore(),
    )

    assert container.registry.count == 1
    assert container.parser_manager.registry is registry
    assert container.startup_warnings == tuple()