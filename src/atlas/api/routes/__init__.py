"""API Routes module."""

from __future__ import annotations

from atlas.api.routes.auth import router as auth_router
from atlas.api.routes.chat import chat_router, openai_router
from atlas.api.routes.chat import router as sessions_router
from atlas.api.routes.memory import router as memory_router
from atlas.api.routes.models import router as models_router
from atlas.api.routes.network import router as network_router
from atlas.api.routes.plugins import router as plugins_router
from atlas.api.routes.providers import router as providers_router
from atlas.api.routes.rag import router as rag_router
from atlas.api.routes.system import router as system_router
from atlas.api.routes.terminal import router as terminal_router
from atlas.api.routes.voice import router as voice_router

__all__ = [
    "auth_router",
    "system_router",
    "models_router",
    "providers_router",
    "chat_router",
    "openai_router",
    "sessions_router",
    "network_router",
    "voice_router",
    "memory_router",
    "plugins_router",
    "terminal_router",
    "rag_router",
]
