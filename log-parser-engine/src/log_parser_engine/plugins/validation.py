from __future__ import annotations

from log_parser_engine.core.base_parser import BaseParser
from log_parser_engine.exceptions import PluginFactoryError


def resolve_parser_instance(loaded_object: object) -> BaseParser:
    """Resolve a loaded plugin object into a concrete parser instance."""
    if isinstance(loaded_object, BaseParser):
        return loaded_object

    if isinstance(loaded_object, type):
        if not issubclass(loaded_object, BaseParser):
            raise PluginFactoryError("loaded class is not a BaseParser subclass")
        try:
            return loaded_object()
        except Exception as exc:  # noqa: BLE001
            raise PluginFactoryError("parser class could not be instantiated") from exc

    if callable(loaded_object):
        try:
            resolved = loaded_object()
        except Exception as exc:  # noqa: BLE001
            raise PluginFactoryError("parser factory could not be invoked") from exc
        if isinstance(resolved, BaseParser):
            return resolved
        raise PluginFactoryError("parser factory did not return a BaseParser")

    raise PluginFactoryError("loaded object is not a valid parser factory")
