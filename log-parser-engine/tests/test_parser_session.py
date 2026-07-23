from __future__ import annotations

from log_parser_engine.batch.options import BatchParseOptions
from log_parser_engine.batch.parser_session import ParserSession
from log_parser_engine.batch.record_reader import SourceRecord
from log_parser_engine.batch.state import ParserRecordStrategy
from log_parser_engine.core import ParserManager, ParserRegistry
from tests.helpers.fake_parser import FakeParser


def test_parser_session_parses_data_item() -> None:
    registry = ParserRegistry([FakeParser("fake", matched=True, confidence=0.9)])
    manager = ParserManager(registry)
    session = ParserSession(
        manager,
        parser_name="fake",
        selected_by="explicit",
        started_at_record=1,
        options=BatchParseOptions(),
        strategy=ParserRecordStrategy(parser_name="fake", mode="line"),
        base_context=None,
    )
    result = session.parse_item(
        SourceRecord(1, 1, 1, "hello", "hello", 5, False, "data"),
        include_raw_record=True,
        include_success_event=True,
        include_failure_details=True,
        source_id="x",
    )
    assert result.status == "success"


def test_parser_session_iis_header_is_not_parsed_as_event() -> None:
    registry = ParserRegistry([FakeParser("iis_w3c", matched=True, confidence=0.9)])
    manager = ParserManager(registry)
    session = ParserSession(
        manager,
        parser_name="iis_w3c",
        selected_by="explicit",
        started_at_record=1,
        options=BatchParseOptions(),
        strategy=ParserRecordStrategy(
            parser_name="iis_w3c", mode="stateful_line", supports_state=True
        ),
        base_context=None,
    )
    result = session.parse_item(
        SourceRecord(
            1, 1, 1, "#Fields: date time", "#Fields: date time", 18, False, "data"
        ),
        include_raw_record=True,
        include_success_event=True,
        include_failure_details=True,
        source_id="x",
    )
    assert result.status == "header"
