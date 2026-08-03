"""Configuration loading for Atlas OS.

Defines a custom YAML settings source and wires it into ``AtlasConfig`` so
configuration precedence (highest to lowest) is:

1. Keyword arguments passed directly to ``AtlasConfig(...)`` / ``load_config``.
2. Environment variables prefixed with ``ATLAS_`` (e.g. ``ATLAS_LOG_LEVEL``).
3. Values from a YAML file (e.g. ``configs/atlas.yaml``).
4. Field defaults declared on ``AtlasConfig``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

from atlas.config.settings import AtlasConfig

logger = logging.getLogger(__name__)


class YamlConfigSettingsSource(PydanticBaseSettingsSource):
    """A pydantic-settings source that reads values from a YAML file."""

    def __init__(
        self, settings_cls: type[BaseSettings], yaml_path: Path | None
    ) -> None:
        super().__init__(settings_cls)
        self._data: dict[str, Any] = {}
        if yaml_path is not None and yaml_path.is_file():
            with yaml_path.open("r", encoding="utf-8") as handle:
                loaded = yaml.safe_load(handle) or {}
            if not isinstance(loaded, dict):
                raise ValueError(
                    f"Config file '{yaml_path}' must contain a YAML mapping at the top level."
                )
            self._data = loaded
        elif yaml_path is not None:
            logger.info(
                "Config file '%s' not found; using defaults and environment variables.",
                yaml_path,
            )

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        return self._data.get(field_name), field_name, False

    def __call__(self) -> dict[str, Any]:
        return dict(self._data)


def _build_config_class(yaml_path: str | Path | None) -> type[AtlasConfig]:
    """Create an ``AtlasConfig`` subclass wired to read *yaml_path*.

    A subclass is used (rather than mutating ``AtlasConfig`` directly) so the
    YAML path can vary per-call without relying on global mutable state.
    """

    resolved = Path(yaml_path) if yaml_path is not None else None

    class _ConfiguredAtlasConfig(AtlasConfig):
        @classmethod
        def settings_customise_sources(
            cls,
            settings_cls: type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
        ) -> tuple[PydanticBaseSettingsSource, ...]:
            return (
                init_settings,
                env_settings,
                YamlConfigSettingsSource(settings_cls, resolved),
                file_secret_settings,
            )

    _ConfiguredAtlasConfig.__name__ = AtlasConfig.__name__
    _ConfiguredAtlasConfig.__qualname__ = AtlasConfig.__qualname__
    return _ConfiguredAtlasConfig


def load_config(path: str | Path | None = None, **overrides: Any) -> AtlasConfig:
    """Build an ``AtlasConfig``, layering YAML and environment sources.

    Args:
        path: Path to a YAML config file such as ``configs/atlas.yaml``. A
            missing file is not an error -- Atlas falls back to defaults and
            environment variables.
        **overrides: Explicit keyword overrides, given the highest
            precedence of all (useful for tests and CLI flags).
    """

    config_class = _build_config_class(path)
    return config_class(**overrides)
