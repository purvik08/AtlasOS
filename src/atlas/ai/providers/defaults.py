"""Centralized provider defaults - single source of truth."""

from __future__ import annotations

from typing import Any

PROVIDER_DEFAULTS: dict[str, dict[str, Any]] = {
    # ===== OpenAI-Compatible =====
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "preferred_models": [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ],
        "fallback_models": ["gpt-3.5-turbo"],
        "supports_functions": True,
        "supports_vision": True,
        "max_context_tokens": 128000,
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "openrouter/auto",
        "extra_headers": {
            "HTTP-Referer": "https://atlas-os.local",
            "X-Title": "Atlas OS",
        },
        "preferred_models": [
            "openrouter/auto",
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4o",
            "google/gemini-pro-1.5",
        ],
        "supports_functions": True,
        "supports_vision": True,
        "max_context_tokens": 200000,
    },
    "nvidia": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "default_model": "meta/llama-3.1-8b-instruct",
        "preferred_models": [
            "meta/llama-3.1-405b-instruct",
            "meta/llama-3.1-70b-instruct",
            "meta/llama-3.1-8b-instruct",
            "nvidia/nemotron-3-ultra",
        ],
        "max_context_tokens": 128000,
    },
    "together": {
        "base_url": "https://api.together.xyz/v1",
        "default_model": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        "preferred_models": [
            "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
            "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
            "mistralai/Mixtral-8x22B-Instruct-v0.1",
        ],
        "max_context_tokens": 128000,
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.1-8b-instant",
        "preferred_models": [
            "llama-3.1-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ],
        "max_context_tokens": 32768,
    },
    "fireworks": {
        "base_url": "https://api.fireworks.ai/inference/v1",
        "default_model": "accounts/fireworks/models/llama-v3p1-8b-instruct",
        "preferred_models": [
            "accounts/fireworks/models/llama-v3p1-405b-instruct",
            "accounts/fireworks/models/llama-v3p1-70b-instruct",
        ],
        "max_context_tokens": 128000,
    },
    "deepinfra": {
        "base_url": "https://api.deepinfra.com/v1/openai",
        "default_model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
        "preferred_models": [
            "meta-llama/Meta-Llama-3.1-405B-Instruct",
            "microsoft/WizardLM-2-8x22B",
        ],
        "max_context_tokens": 128000,
    },
    "perplexity": {
        "base_url": "https://api.perplexity.ai",
        "default_model": "llama-3.1-sonar-large-128k-online",
        "preferred_models": [
            "llama-3.1-sonar-large-128k-online",
            "llama-3.1-sonar-small-128k-online",
        ],
        "max_context_tokens": 128000,
    },
    "xai": {
        "base_url": "https://api.x.ai/v1",
        "default_model": "grok-beta",
        "preferred_models": ["grok-beta", "grok-2"],
        "max_context_tokens": 128000,
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "default_model": "mistral-large-latest",
        "preferred_models": [
            "mistral-large-latest",
            "mistral-small-latest",
            "codestral-latest",
        ],
        "supports_functions": True,
        "max_context_tokens": 32768,
    },
    "cerebras": {
        "base_url": "https://api.cerebras.ai/v1",
        "default_model": "llama3.1-8b",
        "preferred_models": ["llama3.1-70b", "llama3.1-8b"],
        "max_context_tokens": 8192,
    },
    "sambanova": {
        "base_url": "https://api.sambanova.ai/v1",
        "default_model": "Meta-Llama-3.1-8B-Instruct",
        "max_context_tokens": 8192,
    },
    "anyscale": {
        "base_url": "https://api.endpoints.anyscale.com/v1",
        "default_model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
        "max_context_tokens": 128000,
    },
    "lepton": {
        "base_url": "https://api.lepton.ai/v1",
        "default_model": "llama3-8b",
        "max_context_tokens": 8192,
    },
    "replicate": {
        "base_url": "https://api.replicate.com/v1",
        "default_model": "meta/llama-3.1-8b-instruct",
        "max_context_tokens": 128000,
    },
    "azure_openai": {
        "base_url": "",
        "default_model": "gpt-4o-mini",
        "extra_params": {"api_version": "2024-02-15-preview"},
        "max_context_tokens": 128000,
    },
    "cohere_compat": {
        "base_url": "https://api.cohere.ai/v1",
        "default_model": "command-r-plus",
        "max_context_tokens": 128000,
    },
    "ai21_compat": {
        "base_url": "https://api.ai21.com/studio/v1",
        "default_model": "jamba-1.5-large",
        "max_context_tokens": 256000,
    },
    "friendliai": {
        "base_url": "https://api.friendli.ai/v1",
        "default_model": "meta-llama-3.1-8b-instruct",
        "max_context_tokens": 128000,
    },
    "novita": {
        "base_url": "https://api.novita.ai/v3/openai",
        "default_model": "meta-llama/llama-3.1-8b-instruct",
        "max_context_tokens": 128000,
    },

    # ===== Existing Providers (for backward compatibility) =====
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "default_model": "gemini-1.5-flash",
        "preferred_models": [
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.0-pro",
        ],
        "supports_functions": True,
        "supports_vision": True,
        "max_context_tokens": 2000000,
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "preferred_models": ["deepseek-chat", "deepseek-coder"],
        "max_context_tokens": 65536,
    },
    "kimi": {
        "base_url": "https://api.moonshot.cn/v1",
        "default_model": "moonshot-v1-8k",
        "preferred_models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
        "max_context_tokens": 128000,
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen3-0.6b",
        "preferred_models": [
            "qwen3-0.6b",
            "qwen3-1.7b",
            "qwen3-4b",
            "qwen3-8b",
            "qwen3-14b",
            "qwen3-32b",
            "qwen-plus",
            "qwen-max",
            "qwen-turbo",
        ],
        "max_context_tokens": 32768,
        "supports_reasoning": True,
        "reasoning_format": "raw",
    },

    # ===== Custom Implementations =====
    "anthropic": {
        "base_url": "https://api.anthropic.com",
        "default_model": "claude-3-5-sonnet-20241022",
        "preferred_models": [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-3-haiku-20240307",
        ],
        "supports_functions": True,
        "supports_vision": True,
        "max_context_tokens": 200000,
    },
    "vertex_ai": {
        "base_url": "",
        "default_model": "gemini-1.5-pro-001",
        "preferred_models": ["gemini-1.5-pro-001", "gemini-1.5-flash-001"],
        "supports_functions": True,
        "supports_vision": True,
        "max_context_tokens": 2000000,
    },
    "bedrock": {
        "base_url": "",
        "default_model": "anthropic.claude-3-5-sonnet-20240620-v1:0",
        "preferred_models": [
            "anthropic.claude-3-5-sonnet-20240620-v1:0",
            "anthropic.claude-3-haiku-20240307-v1:0",
            "meta.llama3-1-70b-instruct-v1:0",
        ],
        "supports_functions": True,
        "max_context_tokens": 200000,
    },
    "google_ai": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "default_model": "gemini-1.5-pro",
        "preferred_models": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.0-pro"],
        "supports_functions": True,
        "supports_vision": True,
        "max_context_tokens": 2000000,
    },
    "cohere": {
        "base_url": "https://api.cohere.ai/v1",
        "default_model": "command-r-plus-08-2024",
        "preferred_models": ["command-r-plus-08-2024", "command-r-08-2024"],
        "supports_functions": True,
        "max_context_tokens": 128000,
    },
    "ai21": {
        "base_url": "https://api.ai21.com/studio/v1",
        "default_model": "jamba-1.5-large",
        "preferred_models": ["jamba-1.5-large", "jamba-1.5-mini"],
        "max_context_tokens": 256000,
    },
}