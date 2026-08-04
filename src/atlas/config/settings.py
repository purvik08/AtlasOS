"""Application configuration schema for Atlas OS.

Uses Pydantic Settings so configuration can be supplied via defaults, a YAML
file, or environment variables, without ever hardcoding secrets in source.
See :mod:`atlas.config.loader` for how these sources are combined and
prioritized.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AIConfig(BaseModel):
    """Configuration for the Phase 5 AI Engine (``atlas.ai``).

    All fields can be overridden in ``configs/atlas.yaml`` under the ``ai:``
    key, or via environment variables with the ``ATLAS_AI__`` prefix (using
    the double-underscore nested delimiter), e.g.::

        ATLAS_AI__GEMINI_API_KEY=sk-...
        ATLAS_AI__DEFAULT_ROLE=cloud
    """

    default_provider: str = Field(
        default="llama_cpp",
        description="Name of the provider used when no explicit provider is requested.",
    )
    default_role: str = Field(
        default="auto",
        description="Default routing role: 'local', 'cloud', or 'auto'.",
    )
    max_history_messages: int = Field(
        default=50,
        gt=0,
        description="Maximum number of messages retained per conversation session.",
    )
    # Cloud provider API keys.  Left empty by default so the stubs remain
    # functional without any credentials configured.
    gemini_api_key: str = Field(
        default="", description="Google Gemini API key (ATLAS_AI__GEMINI_API_KEY)."
    )
    deepseek_api_key: str = Field(
        default="", description="DeepSeek API key (ATLAS_AI__DEEPSEEK_API_KEY)."
    )
    kimi_api_key: str = Field(
        default="", description="Kimi (Moonshot) API key (ATLAS_AI__KIMI_API_KEY)."
    )
    qwen_api_key: str = Field(
        default="", description="Alibaba Qwen API key (ATLAS_AI__QWEN_API_KEY)."
    )


class AtlasConfig(BaseSettings):
    """Runtime-wide configuration for Atlas OS.

    Only the settings needed by the Runtime Core module are defined here.
    Later modules (AI, voice, network, ...) will extend this with their own
    nested settings sections.
    """

    model_config = SettingsConfigDict(
        env_prefix="ATLAS_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    app_name: str = Field(
        default="Atlas OS", description="Human-readable application name."
    )
    environment: str = Field(
        default="development",
        description="Deployment environment, e.g. development, production.",
    )
    log_level: str = Field(default="INFO", description="Root logging level.")
    log_json: bool = Field(
        default=False, description="Emit structured JSON logs instead of plain text."
    )

    data_dir: str = Field(
        default="./data", description="Directory for persistent runtime data."
    )
    models_dir: str = Field(
        default="./models", description="Directory Atlas scans for local model files."
    )
    plugins_dir: str = Field(
        default="./plugins", description="Directory Atlas scans for plugins."
    )

    health_check_interval_seconds: float = Field(
        default=15.0,
        gt=0,
        description="Interval between background health-check polls.",
    )
    heartbeat_interval_seconds: float = Field(
        default=5.0, gt=0, description="Interval between runtime heartbeat ticks."
    )
    graceful_shutdown_timeout_seconds: float = Field(
        default=10.0,
        gt=0,
        description="Max time to wait for background tasks to cancel during shutdown.",
    )

    # -- AI Engine -------------------------------------------------------

    ai: AIConfig = Field(
        default_factory=AIConfig,
        description="Configuration for the AI Engine (atlas.ai).",
    )
