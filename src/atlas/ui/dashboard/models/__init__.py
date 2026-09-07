"""Data models for Atlas OS Dashboard.

Shared Pydantic models used by both the API service and QML UI components.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SystemInfo(BaseModel):
    """System information from the backend."""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_gb: float = 0.0
    memory_total_gb: float = 0.0
    disk_percent: float = 0.0
    uptime_seconds: float = 0.0
    platform: str = ""
    platform_version: str = ""
    python_version: str = ""
    hostname: str = ""
    ip_address: str = ""
    environment: str = ""
    runtime_state: str = ""
    disk_used_gb: float = 0.0
    disk_total_gb: float = 0.0
    cpu_count: int = 0
    temperature_c: float | None = None
    registered_services: int = 0
    active_tasks: int = 0
    config: dict[str, Any] = Field(default_factory=dict)
    status: str = "OK"
    error: str = ""

    @classmethod
    async def fetch(cls, sdk) -> SystemInfo:
        """Fetch system info from API."""
        try:
            data = await sdk.system_info()
            return cls(
                cpu_percent=data.get("cpu_percent", 0.0),
                memory_percent=data.get("memory_percent", 0.0),
                memory_used_gb=data.get("memory_used_gb", 0.0),
                memory_total_gb=data.get("memory_total_gb", 0.0),
                disk_percent=data.get("disk_percent", 0.0),
                disk_used_gb=data.get("disk_used_gb", 0.0),
                disk_total_gb=data.get("disk_total_gb", 0.0),
                uptime_seconds=data.get("uptime_seconds", 0.0),
                platform=data.get("platform", ""),
                platform_version=data.get("os", ""),
                python_version=data.get("python", ""),
                hostname=data.get("hostname", ""),
                ip_address=data.get("ip_address", ""),
                environment=data.get("environment", ""),
                runtime_state=data.get("runtime_state", ""),
                cpu_count=data.get("cpu_count", 0) or 0,
                temperature_c=data.get("temperature_c"),
                registered_services=data.get("registered_services", 0) or 0,
                active_tasks=data.get("active_tasks", 0) or 0,
                config=data.get("config", {}),
                status=data.get("runtime_state", "OK"),
                error=""
            )
        except Exception:
            return cls()


class ModelInfo(BaseModel):
    """Model information from registry."""
    model_id: str
    display_name: str
    provider_name: str
    loaded: bool = False
    size_bytes: int = 0
    description: str = ""
    quantization: str = ""
    temperature: float = 0.7
    context_size: int = 4096
    port: int = 0
    
    @property
    def size_gb(self) -> float:
        return self.size_bytes / (1024**3) if self.size_bytes > 0 else 0.0


class ModelRegistry(BaseModel):
    """Model registry containing all known models."""
    models: list[ModelInfo] = Field(default_factory=list)

    @classmethod
    async def fetch(cls, sdk) -> ModelRegistry:
        """Fetch model registry from API."""
        try:
            data = await sdk.list_models()
            models = [ModelInfo(**m) for m in data]
            return cls(models=models)
        except Exception:
            return cls()


class ProviderStatus(str):
    """Provider health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNLOADED = "unloaded"


class ProviderHealth(BaseModel):
    """Provider health information."""
    name: str
    status: str = ProviderStatus.HEALTHY
    loaded_models: list[str] = Field(default_factory=list)
    message: str = ""
    last_check: datetime = Field(default_factory=datetime.now)
    error: str = ""

    @classmethod
    async def fetch(cls, sdk, provider_name: str) -> ProviderHealth:
        """Fetch provider health from API."""
        try:
            data = await sdk.provider_health(provider_name)
            return cls(
                name=data.get("provider_name", provider_name),
                status=data.get("status", ProviderStatus.HEALTHY),
                loaded_models=data.get("loaded_models", []),
                message=data.get("message", ""),
            )
        except Exception as e:
            return cls(
                name=provider_name,
                status=ProviderStatus.UNHEALTHY,
                error=str(e),
            )


class ChatMessage(BaseModel):
    """Chat message."""
    role: str
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ChatSession(BaseModel):
    """Chat session."""
    session_id: str
    provider_name: str
    model_id: str
    system_prompt: str = ""
    history: list[ChatMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    async def fetch_all(cls, sdk) -> list[ChatSession]:
        """Fetch all sessions from API."""
        try:
            data = await sdk.list_sessions()
            sessions = []
            for s in data.get("sessions", []):
                history = [ChatMessage(**m) for m in s.get("history", [])]
                sessions.append(cls(
                    session_id=s["session_id"],
                    provider_name=s.get("provider") or "",
                    model_id=s.get("model") or "",
                    system_prompt=s.get("system_prompt", ""),
                    history=history,
                    created_at=datetime.fromisoformat(s["created_at"]),
                ))
            return sessions
        except Exception:
            return []
