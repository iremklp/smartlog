from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from log_parser_engine.core import BaseParser, ParserContext
from log_parser_engine.models import LogEvent, ParseStatus
from log_parser_engine.parsers import (
    IisW3CParser,
    JsonLogParser,
    RedisLogParser,
    Rfc3164SyslogParser,
    Rfc5424SyslogParser,
    WindowsEventXmlParser,
)
from log_parser_engine.parsers.webserver import (
    ApacheNginxAccessLogParser,
    ApacheNginxErrorLogParser,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    ("parser_factory", "fixture", "native_nested_path"),
    [
        pytest.param(
            IisW3CParser,
            FIXTURES / "iis" / "standard.log",
            ("iis",),
            id="iis",
        ),
        pytest.param(
            JsonLogParser,
            FIXTURES / "json" / "generic.json",
            ("json_record",),
            id="json",
        ),
        pytest.param(
            RedisLogParser,
            FIXTURES / "redis" / "server.log",
            ("redis",),
            id="redis",
        ),
        pytest.param(
            Rfc3164SyslogParser,
            FIXTURES / "syslog" / "rfc3164.log",
            ("syslog",),
            id="rfc3164",
        ),
        pytest.param(
            Rfc5424SyslogParser,
            FIXTURES / "syslog" / "rfc5424.log",
            ("syslog",),
            id="rfc5424",
        ),
        pytest.param(
            WindowsEventXmlParser,
            FIXTURES / "windows_event" / "security_event.xml",
            ("windows_event", "event_data"),
            id="windows-event",
        ),
        pytest.param(
            ApacheNginxAccessLogParser,
            FIXTURES / "webserver" / "apache_combined.log",
            None,
            id="web-access",
        ),
        pytest.param(
            ApacheNginxErrorLogParser,
            FIXTURES / "webserver" / "nginx_error.log",
            None,
            id="web-error",
        ),
    ],
)
def test_builtin_parser_events_remain_deeply_immutable(
    parser_factory: Callable[[], BaseParser],
    fixture: Path,
    native_nested_path: tuple[str, ...] | None,
) -> None:
    parser = parser_factory()
    context = ParserContext(
        attributes={
            "immutability_probe": {
                "nested": {"marker": "original"},
                "items": [{"value": 1}],
            }
        }
    )
    result = parser.safe_parse(
        fixture.read_text(encoding="utf-8"),
        context=context,
    )

    assert result.status == ParseStatus.success
    assert len(result.events) == 1
    event = result.events[0]

    with pytest.raises(TypeError, match="mutation"):
        event.attributes["__mutation_probe__"] = True
    with pytest.raises(TypeError, match="mutation"):
        event.tags.append("__mutation_probe__")

    context_probe = event.attributes["immutability_probe"]
    with pytest.raises(TypeError, match="mutation"):
        context_probe["nested"]["marker"] = "changed"
    with pytest.raises(TypeError, match="mutation"):
        context_probe["items"][0]["value"] = 2

    if native_nested_path is not None:
        nested: object = event.attributes
        for key in native_nested_path:
            assert isinstance(nested, dict)
            nested = nested[key]
        assert isinstance(nested, dict)
        with pytest.raises(TypeError, match="mutation"):
            nested["__mutation_probe__"] = True

    serialized = event.model_dump(mode="json")
    assert isinstance(serialized["attributes"], dict)
    assert isinstance(serialized["tags"], list)
    assert LogEvent.model_validate(serialized).model_dump(mode="json") == serialized
