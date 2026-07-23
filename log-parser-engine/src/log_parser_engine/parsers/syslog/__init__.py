from .parser_rfc3164 import Rfc3164SyslogParser
from .parser_rfc5424 import Rfc5424SyslogParser

__plugin_modules__ = ("rfc5424_plugin", "rfc3164_plugin")

__all__ = (
    "Rfc3164SyslogParser",
    "Rfc5424SyslogParser",
)
