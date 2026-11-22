"""AWS Bedrock provider."""

from __future__ import annotations

import json
import time
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from atlas.ai.providers.base import (
    AIProvider,
    ChatMessage,
    ChatResponse,
    ModelInfo,
    ProviderHealth,
    ProviderRole,
    ProviderStatus,
)
from atlas.ai.providers.config import ProviderConfig


class BedrockProvider(AIProvider):
    """AWS Bedrock provider."""

    name = "bedrock"
    role = ProviderRole.CLOUD
    description = "AWS Bedrock (Claude, Llama, etc.)"

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._client: httpx.AsyncClient | None = None
        self._access_key = config.extra_params.get("access_key", "")
        self._secret_key = config.extra_params.get("secret_key", "")
        self._region = config.extra_params.get("region", "us-east-1")

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {"Content-Type": "application/json"}
            headers.update(self._config.extra_headers)
            self._client = httpx.AsyncClient(
                base_url=f"https://bedrock-runtime.{self._region}.amazonaws.com",
                headers=headers,
                timeout=self._config.timeout_seconds,
            )
        return self._client

    def _sign_request(self, request: httpx.Request) -> httpx.Request:
        """Sign request with AWS SigV4. Simplified - in production use botocore."""
        # This is a placeholder - real implementation would use botocore or aws-requests-auth
        return request

    async def list_models(self) -> list[ModelInfo]:
        """List available models."""
        models = []
        for model_id in self._config.preferred_models:
            models.append(ModelInfo(
                model_id=model_id,
                display_name=model_id,
                provider_name=self.name,
                loaded=False,
                description="AWS Bedrock model",
            ))
        return models

    async def chat(
        self,
        messages: list[ChatMessage],
        model_id: str,
        system_prompt: str = "",
        **kwargs: Any,
    ) -> ChatResponse:
        """Non-streaming chat completion."""
        start = time.time()
        client = self._get_client()

        # Convert to Bedrock format (Anthropic Claude format)
        prompt = ""
        if system_prompt:
            prompt += f"System: {system_prompt}\n\n"

        for msg in messages:
            role = "Human" if msg.role == "user" else "Assistant"
            prompt += f"{role}: {msg.content}\n\n"

        prompt += "Assistant:"

        model = model_id or self._config.default_model
        # Determine model provider from model_id
        if "anthropic" in model or "claude" in model.lower():
            payload = {
                "prompt": prompt,
                "max_tokens_to_sample": kwargs.get("max_tokens", 1024),
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.95),
            }
        else:
            # Default to generic format
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": kwargs.get("max_tokens", 1024),
                    "temperature": kwargs.get("temperature", 0.7),
                    "top_p": kwargs.get("top_p", 0.95),
                },
            }

        url = f"/model/{model}/invoke"
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        latency = (time.time() - start) * 1000

        content = data.get("completion", data.get("generation", ""))

        return ChatResponse(
            message=ChatMessage(role="assistant", content=content),
            model_id=model,
            provider_name=self.name,
            prompt_tokens=0,  # Bedrock doesn't always return usage
            completion_tokens=0,
            latency_ms=latency,
        )

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        model_id: str,
        system_prompt: str = "",
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Streaming chat completion."""
        client = self._get_client()

        prompt = ""
        if system_prompt:
            prompt += f"System: {system_prompt}\n\n"

        for msg in messages:
            role = "Human" if msg.role == "user" else "Assistant"
            prompt += f"{role}: {msg.content}\n\n"

        prompt += "Assistant:"

        model = model_id or self._config.default_model
        if "anthropic" in model or "claude" in model.lower():
            payload = {
                "prompt": prompt,
                "max_tokens_to_sample": kwargs.get("max_tokens", 1024),
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.95),
                "stream": True,
            }
        else:
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": kwargs.get("max_tokens", 1024),
                    "temperature": kwargs.get("temperature", 0.7),
                    "top_p": kwargs.get("top_p", 0.95),
                },
                "stream": True,
            }

        url = f"/model/{model}/invoke-with-response-stream"
        async with client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.strip():
                    try:
                        data = json.loads(line)
                        if "completion" in data:
                            yield data["completion"]
                        elif "generation" in data:
                            yield data["generation"]
                    except Exception:
                        pass

    async def health(self) -> ProviderHealth:
        """Check provider health."""
        return ProviderHealth(
            provider_name=self.name,
            status=ProviderStatus.HEALTHY,
            loaded_models=[],
            message="Bedrock available (health check not implemented)",
        )

    async def load_model(self, model_id: str) -> None:
        raise NotImplementedError(
            f"{self.name} is a cloud provider - models don't require local loading"
        )

    async def unload_model(self, model_id: str) -> None:
        raise NotImplementedError(
            f"{self.name} is a cloud provider - models don't require local unloading"
        )

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None