"""Intelligent model selector for automatic provider/model routing."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any




class TaskType(Enum):
    """Type of task for model selection."""

    CHAT = "chat"
    CODING = "coding"
    REASONING = "reasoning"
    CREATIVE = "creative"
    ANALYSIS = "analysis"
    LOCAL = "local"
    FAST = "fast"


@dataclass(slots=True)
class ModelRecommendation:
    """Model recommendation with metadata."""

    provider: str
    model: str
    reason: str
    estimated_cost_per_1m: float  # USD per 1M tokens
    latency_tier: str  # "fast", "balanced", "quality"
    context_window: int
    supports_functions: bool
    supports_vision: bool


class ModelSelector:
    """Selects best model for a task across all providers."""

    # Model preferences by task type
    TASK_PREFERENCES = {
        TaskType.CODING: [
            ("anthropic", "claude-3-5-sonnet-20241022"),
            ("openai", "gpt-4o"),
            ("openrouter", "anthropic/claude-3.5-sonnet"),
            ("deepseek", "deepseek-coder"),
            ("nvidia", "nvidia/nemotron-3-ultra"),
            ("google_ai", "gemini-1.5-pro"),
            ("vertex_ai", "gemini-1.5-pro-001"),
        ],
        TaskType.REASONING: [
            ("openai", "gpt-4o"),
            ("anthropic", "claude-3-5-sonnet-20241022"),
            ("google_ai", "gemini-1.5-pro"),
            ("vertex_ai", "gemini-1.5-pro-001"),
            ("openrouter", "anthropic/claude-3.5-sonnet"),
        ],
        TaskType.CHAT: [
            ("openai", "gpt-4o-mini"),
            ("anthropic", "claude-3-5-haiku-20241022"),
            ("google_ai", "gemini-1.5-flash"),
            ("openrouter", "openrouter/auto"),
            ("nvidia", "meta/llama-3.1-70b-instruct"),
            ("together", "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"),
        ],
        TaskType.CREATIVE: [
            ("openai", "gpt-4o"),
            ("anthropic", "claude-3-5-sonnet-20241022"),
            ("openrouter", "anthropic/claude-3.5-sonnet"),
            ("google_ai", "gemini-1.5-pro"),
        ],
        TaskType.ANALYSIS: [
            ("openai", "gpt-4o"),
            ("anthropic", "claude-3-5-sonnet-20241022"),
            ("google_ai", "gemini-1.5-pro"),
            ("vertex_ai", "gemini-1.5-pro-001"),
        ],
        TaskType.FAST: [
            ("groq", "llama-3.1-8b-instant"),
            ("cerebras", "llama3.1-8b"),
            ("openai", "gpt-4o-mini"),
            ("google_ai", "gemini-1.5-flash"),
            ("together", "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"),
        ],
        TaskType.LOCAL: [
            ("llama_cpp", "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"),
            ("llama_cpp", "phi-3-mini-4k-instruct.Q4_K_M.gguf"),
            ("llama_cpp", "gemma-2-2b-it.Q4_K_M.gguf"),
        ],
    }

    # Model metadata for scoring
    MODEL_METADATA = {
        # Anthropic
        "claude-3-5-sonnet-20241022": {
            "cost_per_1m": 3.0, "latency": "balanced", "context": 200000,
            "functions": True, "vision": True,
        },
        "claude-3-5-haiku-20241022": {
            "cost_per_1m": 0.25, "latency": "fast", "context": 200000,
            "functions": True, "vision": True,
        },
        "claude-3-opus-20240229": {
            "cost_per_1m": 15.0, "latency": "quality", "context": 200000,
            "functions": True, "vision": True,
        },
        # OpenAI
        "gpt-4o": {
            "cost_per_1m": 5.0, "latency": "balanced", "context": 128000,
            "functions": True, "vision": True,
        },
        "gpt-4o-mini": {
            "cost_per_1m": 0.15, "latency": "fast", "context": 128000,
            "functions": True, "vision": True,
        },
        "gpt-4-turbo": {
            "cost_per_1m": 10.0, "latency": "balanced", "context": 128000,
            "functions": True, "vision": True,
        },
        "gpt-3.5-turbo": {
            "cost_per_1m": 0.5, "latency": "fast", "context": 16385,
            "functions": True, "vision": False,
        },
        # Google
        "gemini-1.5-pro": {
            "cost_per_1m": 1.25, "latency": "balanced", "context": 2000000,
            "functions": True, "vision": True,
        },
        "gemini-1.5-flash": {
            "cost_per_1m": 0.075, "latency": "fast", "context": 2000000,
            "functions": True, "vision": True,
        },
        "gemini-1.0-pro": {
            "cost_per_1m": 0.5, "latency": "fast", "context": 32768,
            "functions": True, "vision": False,
        },
        # NVIDIA
        "meta/llama-3.1-405b-instruct": {
            "cost_per_1m": 0.0, "latency": "quality", "context": 128000,
            "functions": False, "vision": False,
        },
        "meta/llama-3.1-70b-instruct": {
            "cost_per_1m": 0.0, "latency": "balanced", "context": 128000,
            "functions": False, "vision": False,
        },
        "meta/llama-3.1-8b-instruct": {
            "cost_per_1m": 0.0, "latency": "fast", "context": 128000,
            "functions": False, "vision": False,
        },
        "nvidia/nemotron-3-ultra": {
            "cost_per_1m": 0.0, "latency": "quality", "context": 128000,
            "functions": False, "vision": False,
        },
        # Together
        "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo": {
            "cost_per_1m": 0.0, "latency": "quality", "context": 128000,
            "functions": False, "vision": False,
        },
        "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo": {
            "cost_per_1m": 0.0, "latency": "balanced", "context": 128000,
            "functions": False, "vision": False,
        },
        "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo": {
            "cost_per_1m": 0.0, "latency": "fast", "context": 128000,
            "functions": False, "vision": False,
        },
        # Groq
        "llama-3.1-70b-versatile": {
            "cost_per_1m": 0.0, "latency": "fast", "context": 32768,
            "functions": False, "vision": False,
        },
        "llama-3.1-8b-instant": {
            "cost_per_1m": 0.0, "latency": "fast", "context": 32768,
            "functions": False, "vision": False,
        },
        "mixtral-8x7b-32768": {
            "cost_per_1m": 0.0, "latency": "fast", "context": 32768,
            "functions": False, "vision": False,
        },
        "gemma2-9b-it": {
            "cost_per_1m": 0.0, "latency": "fast", "context": 32768,
            "functions": False, "vision": False,
        },
        # xAI
        "grok-beta": {
            "cost_per_1m": 0.0, "latency": "balanced", "context": 128000,
            "functions": False, "vision": False,
        },
        # Mistral
        "mistral-large-latest": {
            "cost_per_1m": 0.0, "latency": "balanced", "context": 32768,
            "functions": True, "vision": False,
        },
        "codestral-latest": {
            "cost_per_1m": 0.0, "latency": "fast", "context": 32768,
            "functions": True, "vision": False,
        },
        # DeepSeek
        "deepseek-chat": {
            "cost_per_1m": 0.0, "latency": "balanced", "context": 65536,
            "functions": False, "vision": False,
        },
        "deepseek-coder": {
            "cost_per_1m": 0.0, "latency": "balanced", "context": 65536,
            "functions": False, "vision": False,
        },
        # Local models (cost = 0, but requires hardware)
        "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf": {
            "cost_per_1m": 0.0, "latency": "fast", "context": 2048,
            "functions": False, "vision": False,
        },
        "phi-3-mini-4k-instruct.Q4_K_M.gguf": {
            "cost_per_1m": 0.0, "latency": "fast", "context": 4096,
            "functions": False, "vision": False,
        },
        "gemma-2-2b-it.Q4_K_M.gguf": {
            "cost_per_1m": 0.0, "latency": "fast", "context": 8192,
            "functions": False, "vision": False,
        },
    }

    def __init__(
        self,
        available_providers: dict[str, Any] | None = None,
        prefer_local: bool = False,
        max_cost_per_request: float = 0.0,
    ) -> None:
        self._available_providers = available_providers or {}
        self._prefer_local = prefer_local
        self._max_cost_per_request = max_cost_per_request  # 0 = unlimited

    def update_available_providers(self, providers: dict[str, Any]) -> None:
        """Update the list of available providers."""
        self._available_providers = providers

    def select(
        self,
        task: TaskType,
        prefer_local: bool | None = None,
        max_cost: float | None = None,
        require_functions: bool = False,
        require_vision: bool = False,
        min_context: int = 0,
    ) -> ModelRecommendation | None:
        """Select best model for a task."""
        effective_local = prefer_local if prefer_local is not None else self._prefer_local
        effective_max_cost = max_cost if max_cost is not None else self._max_cost_per_request

        # Get candidate models for task
        candidates = self.TASK_PREFERENCES.get(task, [])
        if not candidates:
            candidates = self.TASK_PREFERENCES[TaskType.CHAT]

        # If prefer_local, prioritize local models
        if effective_local:
            local_candidates = self.TASK_PREFERENCES.get(TaskType.LOCAL, [])
            candidates = local_candidates + [c for c in candidates if c[0] != "llama_cpp"]

        # Score and filter candidates
        scored = []
        for provider, model in candidates:
            # Check if provider is available
            if provider not in self._available_providers:
                continue

            provider_obj = self._available_providers[provider]
            if not getattr(provider_obj, "_config", None) or not provider_obj._config.api_key:
                continue

            # Get metadata
            meta = self.MODEL_METADATA.get(model, {})
            cost = meta.get("cost_per_1m", 0.0)
            latency = meta.get("latency", "balanced")
            context = meta.get("context", 4096)
            functions = meta.get("functions", False)
            vision = meta.get("vision", False)

            # Filter by requirements
            if require_functions and not functions:
                continue
            if require_vision and not vision:
                continue
            if min_context and context < min_context:
                continue
            if effective_max_cost > 0 and cost > 0 and cost > effective_max_cost:
                continue

            # Score: lower is better
            # Prioritize: cost (if limited), latency preference, context
            score = 0
            if effective_max_cost > 0:
                score += cost * 1000
            if latency == "fast":
                score += 0
            elif latency == "balanced":
                score += 10
            else:
                score += 50
            score -= context / 10000  # Prefer larger context

            scored.append((score, provider, model, meta))

        if not scored:
            return None

        # Sort by score
        scored.sort(key=lambda x: x[0])
        best = scored[0]

        _, provider, model, meta = best
        return ModelRecommendation(
            provider=provider,
            model=model,
            reason=f"Best match for {task.value} (cost: ${meta.get('cost_per_1m', 0):.2f}/1M tokens, latency: {meta.get('latency', 'balanced')})",
            estimated_cost_per_1m=meta.get("cost_per_1m", 0.0),
            latency_tier=meta.get("latency", "balanced"),
            context_window=meta.get("context", 4096),
            supports_functions=meta.get("functions", False),
            supports_vision=meta.get("vision", False),
        )

    def get_all_recommendations(
        self,
        task: TaskType,
        limit: int = 5,
    ) -> list[ModelRecommendation]:
        """Get multiple recommendations for a task."""
        effective_local = self._prefer_local
        candidates = self.TASK_PREFERENCES.get(task, [])
        if not candidates:
            candidates = self.TASK_PREFERENCES[TaskType.CHAT]

        if effective_local:
            local_candidates = self.TASK_PREFERENCES.get(TaskType.LOCAL, [])
            candidates = local_candidates + [c for c in candidates if c[0] != "llama_cpp"]

        recommendations = []
        for provider, model in candidates:
            if provider not in self._available_providers:
                continue
            provider_obj = self._available_providers[provider]
            if not getattr(provider_obj, "_config", None) or not provider_obj._config.api_key:
                continue

            meta = self.MODEL_METADATA.get(model, {})
            recommendations.append(ModelRecommendation(
                provider=provider,
                model=model,
                reason=f"Suitable for {task.value}",
                estimated_cost_per_1m=meta.get("cost_per_1m", 0.0),
                latency_tier=meta.get("latency", "balanced"),
                context_window=meta.get("context", 4096),
                supports_functions=meta.get("functions", False),
                supports_vision=meta.get("vision", False),
            ))

        return recommendations[:limit]