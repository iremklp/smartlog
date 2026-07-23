from __future__ import annotations

import threading

import pytest

from log_parser_engine.core import ParserRegistry
from log_parser_engine.exceptions import (
    ParserAlreadyRegisteredError,
    ParserNotFoundError,
)
from log_parser_engine.models import LogSourceType
from tests.helpers.fake_parser import FakeParser


def test_registry_allows_empty_initialization() -> None:
    registry = ParserRegistry()
    assert registry.count == 0
    assert registry.enabled_count == 0
    assert len(registry) == 0


def test_registry_registers_parsers_in_order() -> None:
    registry = ParserRegistry()
    first = FakeParser("json")
    second = FakeParser("yaml")
    registry.register(first)
    registry.register(second)
    assert registry.count == 2
    assert registry.list_parsers()[0].name == "json"
    assert registry.list_parsers()[1].name == "yaml"


def test_registry_rejects_duplicate_parser_name() -> None:
    registry = ParserRegistry()
    registry.register(FakeParser("json"))
    with pytest.raises(ParserAlreadyRegisteredError):
        registry.register(FakeParser("json"))


def test_registry_rejects_case_insensitive_duplicates() -> None:
    registry = ParserRegistry()
    registry.register(FakeParser("JSON"))
    with pytest.raises(ParserAlreadyRegisteredError):
        registry.register(FakeParser("json"))


def test_registry_uses_explicit_enabled_override() -> None:
    registry = ParserRegistry()
    parser = FakeParser("json", enabled=False)
    registration = registry.register(parser, enabled=True)
    assert registration.enabled is True
    assert registry.get_registration("json").enabled is True


def test_registry_replaces_existing_parser_when_requested() -> None:
    registry = ParserRegistry()
    registry.register(FakeParser("json"))
    replacement = FakeParser("json", version="2.0.0")
    registration = registry.register(replacement, replace=True)
    assert registration.parser_version == "2.0.0"
    assert registry.get("json").version == "2.0.0"


def test_registry_get_and_contains_work_case_insensitively() -> None:
    registry = ParserRegistry()
    registry.register(FakeParser("json"))
    assert registry.get("JSON").name == "json"
    assert registry.contains("json") is True
    assert registry.contains("missing") is False


def test_registry_lists_enabled_only_and_all_parsers() -> None:
    registry = ParserRegistry()
    registry.register(FakeParser("json", enabled=True))
    registry.register(FakeParser("yaml", enabled=False))
    assert len(registry.list_parsers()) == 2
    assert len(registry.list_parsers(enabled_only=True)) == 1
    assert len(registry.list_registrations(enabled_only=True)) == 1


def test_registry_filters_by_source_type_and_tag() -> None:
    registry = ParserRegistry()
    registry.register(
        FakeParser("json", source_type=LogSourceType.JSON, tags=("app",))
    )
    registry.register(
        FakeParser("redis", source_type=LogSourceType.REDIS, tags=("infra",))
    )
    assert len(registry.find_by_source_type(LogSourceType.JSON)) == 1
    assert len(registry.find_by_tag("APP")) == 1


def test_registry_enable_disable_and_idempotency() -> None:
    registry = ParserRegistry()
    registry.register(FakeParser("json"))
    disabled = registry.disable("json")
    assert disabled.enabled is False
    assert registry.enable("json").enabled is True
    assert registry.set_enabled("json", False).enabled is False
    assert registry.set_enabled("json", False).enabled is False


def test_registry_unregisters_and_clears() -> None:
    registry = ParserRegistry()
    registry.register(FakeParser("json"))
    registry.register(FakeParser("yaml"))
    removed = registry.unregister("json")
    assert removed.name == "json"
    assert registry.count == 1
    registry.clear()
    assert registry.count == 0


def test_registry_rejects_missing_parser() -> None:
    registry = ParserRegistry()
    with pytest.raises(ParserNotFoundError):
        registry.get("json")
    with pytest.raises(ParserNotFoundError):
        registry.disable("json")


def test_registry_rejects_invalid_parser_type() -> None:
    registry = ParserRegistry()
    with pytest.raises(TypeError):
        registry.register(object())  # type: ignore[arg-type]


def test_registry_thread_safe_registration_is_consistent() -> None:
    registry = ParserRegistry()
    errors: list[Exception] = []

    def worker(name: str) -> None:
        try:
            registry.register(FakeParser(name))
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [
        threading.Thread(target=worker, args=(f"parser_{index}",))
        for index in range(5)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert registry.count == 5
    assert len(errors) == 0
