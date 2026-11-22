"""Provider factory for centralized instantiation."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from atlas.ai.providers.base import AIProvider
    from atlas.config.settings import AIConfig

from atlas.ai.providers.config import ProviderConfig
from atlas.ai.providers.defaults import PROVIDER_DEFAULTS


class ProviderFactory:
    """Centralized provider instantiation."""

    _PROVIDER_MAP: dict[str, tuple[str, str]] = {
        # OpenAI-compatible
        "openai": ("atlas.ai.providers.openai", "OpenAIProvider"),
        "openrouter": ("atlas.ai.providers.openrouter", "OpenRouterProvider"),
        "nvidia": ("atlas.ai.providers.nvidia", "NvidiaProvider"),
        "together": ("atlas.ai.providers.together", "TogetherProvider"),
        "groq": ("atlas.ai.providers.groq", "GroqProvider"),
        "fireworks": ("atlas.ai.providers.fireworks", "FireworksProvider"),
        "deepinfra": ("atlas.ai.providers.deepinfra", "DeepInfraProvider"),
        "perplexity": ("atlas.ai.providers.perplexity", "PerplexityProvider"),
        "xai": ("atlas.ai.providers.xai", "XAIProvider"),
        "mistral": ("atlas.ai.providers.mistral", "MistralProvider"),
        "cerebras": ("atlas.ai.providers.cerebras", "CerebrasProvider"),
        "sambanova": ("atlas.ai.providers.sambanova", "SambaNovaProvider"),
        "anyscale": ("atlas.ai.providers.anyscale", "AnyscaleProvider"),
        "lepton": ("atlas.ai.providers.lepton", "LeptonProvider"),
        "replicate": ("atlas.ai.providers.replicate", "ReplicateProvider"),
        "azure_openai": ("atlas.ai.providers.azure_openai", "AzureOpenAIProvider"),
        "cohere_compat": ("atlas.ai.providers.cohere_compat", "CohereCompatProvider"),
        "ai21_compat": ("atlas.ai.providers.ai21_compat", "AI21CompatProvider"),
        "friendliai": ("atlas.ai.providers.friendliai", "FriendliAIProvider"),
        "novita": ("atlas.ai.providers.novita", "NovitaProvider"),
        # Existing core providers (for backward compatibility)
        "gemini": ("atlas.ai.providers.gemini", "GeminiProvider"),
        "deepseek": ("atlas.ai.providers.deepseek", "DeepSeekProvider"),
        "kimi": ("atlas.ai.providers.kimi", "KimiProvider"),
        "qwen": ("atlas.ai.providers.qwen", "QwenProvider"),
        # Custom implementations
        "anthropic": ("atlas.ai.providers.anthropic", "AnthropicProvider"),
        "vertex_ai": ("atlas.ai.providers.vertex_ai", "VertexAIProvider"),
        "bedrock": ("atlas.ai.providers.bedrock", "BedrockProvider"),
        "google_ai": ("atlas.ai.providers.google_ai", "GoogleAIProvider"),
        "cohere": ("atlas.ai.providers.cohere", "CohereProvider"),
        "ai21": ("atlas.ai.providers.ai21", "AI21Provider"),
    }

    # Core providers that should be created even without API keys (for testing/health checks)
    _CORE_PROVIDERS = frozenset({"gemini", "deepseek", "kimi", "qwen"})

    @classmethod
    def create_all(cls, ai_config: AIConfig) -> list[AIProvider]:
        """Create all configured providers."""
        providers: list[AIProvider] = []
        for name in cls._PROVIDER_MAP:
            config = cls._build_config(name, ai_config)
            if config.api_key or name in cls._CORE_PROVIDERS:  # Always create core providers
                provider = cls._instantiate(config)
                providers.append(provider)
        return providers

    @classmethod
    def create(cls, name: str, ai_config: AIConfig, allow_no_key: bool = False) -> AIProvider | None:
        """Create a single provider by name."""
        if name not in cls._PROVIDER_MAP:
            return None
        config = cls._build_config(name, ai_config)
        if not config.api_key and not allow_no_key and name not in cls._CORE_PROVIDERS:
            return None
        return cls._instantiate(config)

    @classmethod
    def _build_config(cls, name: str, ai_config: AIConfig) -> ProviderConfig:
        """Build ProviderConfig from AIConfig with provider-specific defaults."""
        # Map provider name to config attributes
        key_attr = f"{name}_api_key"
        url_attr = f"{name}_base_url"
        model_attr = f"{name}_default_model"

        api_key = getattr(ai_config, key_attr, "")
        if not api_key and name not in cls._CORE_PROVIDERS:
            return ProviderConfig(name=name)

        # Provider-specific defaults
        defaults = PROVIDER_DEFAULTS.get(name, {})
        return ProviderConfig(
            name=name,
            api_key=api_key,
            base_url=getattr(ai_config, url_attr, defaults.get("base_url", "")),
            default_model=getattr(ai_config, model_attr, defaults.get("default_model", "")),
            extra_headers=defaults.get("extra_headers", {}),
            extra_params=defaults.get("extra_params", {}),
            preferred_models=defaults.get("preferred_models", []),
            fallback_models=defaults.get("fallback_models", []),
            supports_functions=defaults.get("supports_functions", False),
            supports_vision=defaults.get("supports_vision", False),
            max_context_tokens=defaults.get("max_context_tokens", 4096),
        )

    @classmethod
    def _instantiate(cls, config: ProviderConfig) -> AIProvider:
        """Dynamically import and instantiate provider class."""
        module_path, class_name = cls._PROVIDER_MAP[config.name]
        module = __import__(module_path, fromlist=[class_name])
        provider_class = getattr(module, class_name)
        return provider_class(config=config)