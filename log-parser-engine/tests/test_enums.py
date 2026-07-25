from log_parser_engine.models import (
    ErrorType,
    LogSeverity,
    LogSourceType,
    ParseStatus,
)


def test_enum_wire_values_are_lowercase() -> None:
    assert LogSeverity.ERROR.value == "error"
    assert LogSourceType.WINDOWS_EVENT.value == "windows_event"
    assert ParseStatus.SUCCESS.value == "success"
    assert ParseStatus.FAILURE.value == "failed"
    assert ErrorType.EMPTY_INPUT.value == "empty_input"


def test_enum_member_aliases_resolve_to_the_same_value() -> None:
    assert LogSeverity.ERROR is LogSeverity.error
    assert LogSourceType.APPLICATION is LogSourceType.application
    assert ParseStatus.FAILURE is ParseStatus.FAILED
    assert ParseStatus.FAILURE is ParseStatus.failed
    assert ErrorType.UNKNOWN_FORMAT is ErrorType.unknown_format


def test_string_conversion_uses_the_canonical_wire_value() -> None:
    assert str(LogSeverity.ERROR) == "error"
    assert str(LogSourceType.APPLICATION) == "application"
    assert str(ParseStatus.FAILURE) == "failed"
    assert str(ErrorType.INVALID_TIMESTAMP) == "invalid_timestamp"


def test_legacy_uppercase_wire_values_remain_accepted() -> None:
    assert LogSeverity("ERROR") is LogSeverity.ERROR
    assert LogSourceType("APPLICATION") is LogSourceType.APPLICATION
    assert ParseStatus("SUCCESS") is ParseStatus.SUCCESS
    assert ParseStatus("FAILURE") is ParseStatus.FAILURE
    assert ErrorType("EMPTY_INPUT") is ErrorType.EMPTY_INPUT
    assert ErrorType("INVALID_ENCODING") is ErrorType.INVALID_ENCODING


def test_enum_input_is_trimmed_and_case_insensitive() -> None:
    assert LogSeverity(" Warning ") is LogSeverity.WARNING
    assert LogSourceType("Windows_Event") is LogSourceType.WINDOWS_EVENT
    assert ParseStatus("FaIlEd") is ParseStatus.FAILURE
    assert ParseStatus("failure") is ParseStatus.FAILURE
    assert ErrorType("Validation_Failed") is ErrorType.VALIDATION_FAILED
