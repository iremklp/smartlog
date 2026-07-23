from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .plugin_load_result import PluginLoadResult


class PluginDiscoveryResult(BaseModel):
    """Immutable summary of a plugin discovery run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    results: tuple[PluginLoadResult, ...] = Field(default_factory=tuple)
    discovered_count: int = Field(default=0, ge=0)
    loaded_count: int = Field(default=0, ge=0)
    registered_count: int = Field(default=0, ge=0)
    failed_count: int = Field(default=0, ge=0)
    replaced_count: int = Field(default=0, ge=0)
    duration_ms: float = Field(default=0.0, ge=0.0)

    @model_validator(mode="before")
    @classmethod
    def validate_counts(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data

        results = data.get("results", ())
        if not isinstance(results, tuple):
            results = tuple(results)

        loaded_count = sum(1 for result in results if result.success)
        registered_count = sum(1 for result in results if result.registered)
        failed_count = sum(1 for result in results if not result.success)
        replaced_count = sum(1 for result in results if result.replaced_existing)

        data.setdefault("discovered_count", len(results))
        data.setdefault("loaded_count", loaded_count)
        data.setdefault("registered_count", registered_count)
        data.setdefault("failed_count", failed_count)
        data.setdefault("replaced_count", replaced_count)

        if data["registered_count"] > data["loaded_count"]:
            raise ValueError("registered_count cannot exceed loaded_count")
        if data["replaced_count"] > data["registered_count"]:
            raise ValueError("replaced_count cannot exceed registered_count")
        return data

    @property
    def all_successful(self) -> bool:
        return self.failed_count == 0

    @property
    def has_failures(self) -> bool:
        return self.failed_count > 0

    @property
    def loaded_identifiers(self) -> tuple[str, ...]:
        identifiers = []
        for result in self.results:
            identifier = result.identifier
            if identifier is not None:
                identifiers.append(identifier)
        return tuple(identifiers)
