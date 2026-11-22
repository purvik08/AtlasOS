"""Abstract provider interface and shared data models for the Atlas OS AI Engine.

Every AI provider (local or cloud) must implement :class:`AIProvider`.  The
data models defined here are the *single source of truth* for the message
format flowing through the entire AI subsystem — from the CLI down to the
inference backend and back up to the session manager.

Design notes
------------
* All I/O is async so the FastAPI server and the CLI can both consume it
  without blocking.
* ``stream_chat`` returns an ``AsyncIterator[str]`` of *token chunks* so
  callers can write to a terminal or SSE stream incrementally.
* ``health()`` is a lightweight ping — it must not perform inference.
* Provider implementations are *stubs*: the interface is complete and
  production-quality; the inference backends will be plugged in later
  without touching any other module.
"""

from __future__ import annotations

import enum
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ProviderRole(str, enum.Enum):
    """The capability role a provider fulfils.

    ``LOCAL``  — inference runs on-device (llama.cpp / GGUF).
    ``CLOUD``  — inference is delegated to a remote API.
    ``AUTO``   — the router decides which provider to use.
    """

    LOCAL = "local"
    CLOUD = "cloud"
    AUTO = "auto"


class MessageRole(str, enum.Enum):
    """Role of a participant in a conversation turn."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ProviderStatus(str, enum.Enum):
    """Coarse health state reported by :meth:`AIProvider.health`."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNLOADED = "unloaded"


# ---------------------------------------------------------------------------
# Shared Pydantic models
# ---------------------------------------------------------------------------


class Message(BaseModel):
    """A single turn in a conversation.

    Attributes
    ----------
    role:
        Who produced this message.
    content:
        The raw text of the message.
    timestamp:
        UTC time the message was created.  Defaults to *now*.
    metadata:
        Arbitrary key/value pairs (e.g. token counts, latency).
    """

    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    """The complete response returned by :meth:`AIProvider.chat`.

    Attributes
    ----------
    message:
        The assistant's reply.
    provider_name:
        Which provider generated the response.
    model_id:
        Which model was used.
    prompt_tokens:
        Approximate number of tokens in the prompt (``-1`` if unknown).
    completion_tokens:
        Approximate number of tokens in the response (``-1`` if unknown).
    latency_ms:
        Wall-clock latency in milliseconds (``-1`` if not measured).
    """

    message: Message
    provider_name: str
    model_id: str
    prompt_tokens: int = -1
    completion_tokens: int = -1
    latency_ms: float = -1.0


class ModelInfo(BaseModel):
    """Metadata for a single model known to a provider.

    Attributes
    ----------
    model_id:
        Stable identifier (e.g. ``"qwen2-7b-q4"``, ``"gemini-1.5-flash"``).
    display_name:
        Human-readable name.
    provider_name:
        Name of the owning provider.
    loaded:
        Whether the model is currently resident in memory / active.
    size_bytes:
        On-disk or in-memory size.  ``-1`` if unknown.
    description:
        Optional freeform description.
    """

    model_id: str
    display_name: str
    provider_name: str
    loaded: bool = False
    size_bytes: int = -1
    description: str = ""


class ProviderHealth(BaseModel):
    """Health report returned by :meth:`AIProvider.health`.

    Attributes
    ----------
    provider_name:
        Name of the reporting provider.
    status:
        Coarse health classification.
    loaded_models:
        IDs of models currently loaded.
    message:
        Human-readable explanation (especially useful when not healthy).
    checked_at:
        When this report was generated.
    """

    provider_name: str
    status: ProviderStatus = ProviderStatus.HEALTHY
    loaded_models: list[str] = Field(default_factory=list)
    message: str = ""
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProviderInfo(BaseModel):
    """Summary descriptor for a provider as seen by the router/manager."""

    name: str
    role: ProviderRole
    description: str = ""
    available: bool = True


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------


class AIProvider(ABC):
    """Contract every Atlas OS AI provider must satisfy.

    Subclasses represent distinct inference backends or cloud APIs.  They are
    discovered and registered automatically by :class:`~atlas.ai.manager.AIManager`
    on startup.

    All methods are *async* so they can be used without blocking inside FastAPI
    request handlers, CLI commands, or background tasks.
    """

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique stable identifier, e.g. ``"llama_cpp"``."""

    @property
    @abstractmethod
    def role(self) -> ProviderRole:
        """The capability role of this provider."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable one-line description shown in ``atlas provider list``."""

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @abstractmethod
    async def load_model(self, model_id: str) -> None:
        """Make *model_id* available for inference.

        For local providers this typically means mapping the GGUF file into
        RAM.  For cloud providers it may be a no-op or a pre-warm API call.

        Raises
        ------
        ValueError
            If *model_id* is not known to this provider.
        RuntimeError
            If loading fails for any other reason.
        """

    @abstractmethod
    async def unload_model(self, model_id: str) -> None:
        """Release resources held by *model_id*.

        Safe to call even if the model is not currently loaded (idempotent).
        """

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    @abstractmethod
    async def list_models(self) -> list[ModelInfo]:
        """Return metadata for every model this provider knows about."""

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        model_id: str,
        **kwargs: Any,
    ) -> ChatResponse:
        """Produce a single complete response given a conversation history.

        Parameters
        ----------
        messages:
            Ordered list of conversation turns ending with the latest user
            message.
        model_id:
            The model to use for this request.
        **kwargs:
            Provider-specific generation parameters (temperature, max_tokens,
            top_p, …).

        Returns
        -------
        ChatResponse
            The assistant's reply with associated metadata.
        """

    @abstractmethod
    def stream_chat(
        self,
        messages: list[Message],
        model_id: str,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Yield token chunks as they are produced.

        Parameters match :meth:`chat`.  Each yielded ``str`` is a raw text
        fragment; callers accumulate them to reconstruct the full response.

        This method returns an *async iterator* (it should be implemented as
        an ``async def`` generator).
        """

    # ------------------------------------------------------------------
    # Operations
    # ------------------------------------------------------------------

    @abstractmethod
    async def health(self) -> ProviderHealth:
        """Return a lightweight health report without performing inference."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def info(self) -> ProviderInfo:
        """Return a :class:`ProviderInfo` descriptor for this provider."""
        return ProviderInfo(
            name=self.name,
            role=self.role,
            description=self.description,
        )

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={self.name!r}, role={self.role.value!r})"
