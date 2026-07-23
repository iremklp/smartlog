from __future__ import annotations

from log_parser_engine.core import ParserManager, ParserRegistry
from log_parser_engine.models import ErrorType, ParseStatus
from tests.helpers.fake_parser import FakeParser


def test_manager_constructs_with_registry() -> None:
    registry = ParserRegistry()
    manager = ParserManager(registry)
    assert manager.registry is registry
    assert manager.minimum_confidence == 0.6
    assert manager.ambiguity_margin == 0.05


def test_manager_selects_available_parser() -> None:
    registry = ParserRegistry()
    parser = FakeParser("json", matched=True, confidence=0.9, reason="json")
    registry.register(parser)
    manager = ParserManager(registry)
    selection = manager.select_parser("hello")
    assert selection.selected is True
    assert selection.parser_name == "json"


def test_manager_skips_disabled_parser() -> None:
    registry = ParserRegistry()
    registry.register(FakeParser("json", enabled=False, matched=True, confidence=0.9))
    manager = ParserManager(registry)
    selection = manager.select_parser("hello")
    assert selection.selected is False


def test_manager_uses_updated_registry_snapshot() -> None:
    registry = ParserRegistry()
    manager = ParserManager(registry)
    selection = manager.select_parser("hello")
    assert selection.selected is False
    registry.register(FakeParser("json", matched=True, confidence=0.95, reason="json"))
    next_selection = manager.select_parser("hello")
    assert next_selection.selected is True


def test_manager_parse_returns_successful_parse_result() -> None:
    registry = ParserRegistry()
    parser = FakeParser("json", matched=True, confidence=0.9, reason="json")
    registry.register(parser)
    manager = ParserManager(registry)
    result = manager.parse("hello")
    assert result.status == ParseStatus.success


def test_manager_parse_returns_failure_when_no_parser_selected() -> None:
    registry = ParserRegistry()
    manager = ParserManager(registry)
    result = manager.parse("hello")
    assert result.status == ParseStatus.failed
    assert result.errors[0].error_type == ErrorType.DETECTION_FAILED


def test_manager_parse_with_manual_parser() -> None:
    registry = ParserRegistry()
    parser = FakeParser("json", matched=True, confidence=0.9, reason="json")
    registry.register(parser)
    manager = ParserManager(registry)
    result = manager.parse_with("JSON", "hello")
    assert result.status == ParseStatus.success


def test_manager_parse_with_disabled_parser_requires_allow_disabled() -> None:
    registry = ParserRegistry()
    registry.register(FakeParser("json", enabled=False, matched=True, confidence=0.9))
    manager = ParserManager(registry)
    result = manager.parse_with("json", "hello")
    assert result.status == ParseStatus.failed
    assert result.errors[0].error_type == ErrorType.INTERNAL_ERROR
    enabled_result = manager.parse_with("json", "hello", allow_disabled=True)
    assert enabled_result.status == ParseStatus.success


def test_manager_exposes_available_and_enabled_registrations() -> None:
    registry = ParserRegistry()
    registry.register(FakeParser("json"))
    registry.register(FakeParser("yaml", enabled=False))
    manager = ParserManager(registry)
    assert len(manager.available_parsers()) == 2
    assert len(manager.enabled_parsers()) == 1
