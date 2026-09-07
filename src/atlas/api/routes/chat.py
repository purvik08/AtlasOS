"""Chat routes for Atlas OS API."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from atlas.api.auth import require_auth
from atlas.runtime.application import AtlasApplication

router = APIRouter()
openai_router = APIRouter()


class ChatMessage(BaseModel):
    """Chat message."""
    role: str = Field(pattern="^(system|user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    """Chat completion request."""
    model: str
    messages: list[ChatMessage]
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, gt=0)
    top_p: float = Field(default=0.95, ge=0.0, le=1.0)
    stream: bool = False
    session_id: str | None = None


class ChatResponse(BaseModel):
    """Chat completion response."""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[dict[str, Any]]
    usage: dict[str, int]


class SessionCreateRequest(BaseModel):
    """Create session request."""
    provider: str | None = None
    model: str | None = None
    role: str | None = None
    system_prompt: str = ""


def get_app(request: Request) -> AtlasApplication:
    """Dependency to get AtlasApplication from request state."""
    return request.app.state.atlas_app


def get_os_ai(app: AtlasApplication = Depends(get_app)) -> Any:
    """Resolve or construct the shared AtlasOSAI layer."""
    if "os_ai" in app.container:
        return app.container.resolve("os_ai")

    from atlas.ai.os_ai import AtlasOSAI
    from atlas.rag.service import RAGService

    ai_mgr = app.container.resolve("ai_manager") if "ai_manager" in app.container else None
    rag_svc = app.container.resolve("rag_service") if "rag_service" in app.container else None
    if rag_svc is None:
        rag_svc = RAGService(data_dir=getattr(app.config, "data_dir", "./data"))
        app.container.register_instance("rag_service", rag_svc)

    os_ai = AtlasOSAI(ai_manager=ai_mgr, rag_service=rag_svc, container=app.container)
    app.container.register_instance("os_ai", os_ai)
    return os_ai


# Standard Atlas OS chat endpoints
chat_router = APIRouter(prefix="/chat", tags=["chat"])


@chat_router.post("/completions", response_model=ChatResponse)
async def chat_completion(
    request: ChatRequest,
    app: AtlasApplication = Depends(get_app),
    os_ai: Any = Depends(get_os_ai),
    api_key: str = Depends(require_auth),
) -> ChatResponse:
    """Standard chat completion routed through OS AI layer."""
    last_msg = request.messages[-1]
    user_content = last_msg.content if last_msg.role == "user" else ""
    
    try:
        res = await os_ai.process_message(
            user_message=user_content,
            session_id=request.session_id,
            model_id=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    
    prompt_tokens = sum(len(m.content.split()) for m in request.messages)
    completion_tokens = len(res.content.split())

    return ChatResponse(
        id=f"chatcmpl-{int(time.time())}",
        created=int(time.time()),
        model=request.model,
        choices=[{
            "index": 0,
            "message": {"role": "assistant", "content": res.content},
            "finish_reason": "stop",
        }],
        usage={
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    )


@chat_router.post("/completions/stream")
async def chat_completion_stream(
    request: ChatRequest,
    app: AtlasApplication = Depends(get_app),
    os_ai: Any = Depends(get_os_ai),
    api_key: str = Depends(require_auth),
) -> StreamingResponse:
    """Streaming chat completion routed through OS AI layer."""
    last_msg = request.messages[-1]
    user_content = last_msg.content if last_msg.role == "user" else ""
    
    async def generate() -> AsyncIterator[str]:
        import json
        try:
            async for chunk in os_ai.process_stream(
                user_message=user_content,
                session_id=request.session_id,
                model_id=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                top_p=request.top_p,
            ):
                data = {
                    "id": "chatcmpl-stream",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": request.model,
                    "choices": [{
                        "index": 0,
                        "delta": {"content": chunk},
                        "finish_reason": None,
                    }],
                }
                yield f"data: {json.dumps(data)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            error_data = {"error": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )



# Sessions endpoints
@router.post("/sessions", tags=["sessions"])
async def create_session(
    request: SessionCreateRequest,
    app: AtlasApplication = Depends(get_app),
    api_key: str = Depends(require_auth),
) -> dict[str, Any]:
    """Create a new chat session."""
    manager = app.container.resolve("ai_manager")
    
    from atlas.ai.providers.base import ProviderRole
    role = ProviderRole(request.role) if request.role else None
    
    session = manager.new_session(
        provider_name=request.provider,
        role=role,
        model_id=request.model,
        system_prompt=request.system_prompt,
    )
    
    return {
        "session_id": session.session_id,
        "provider": session.provider_name,
        "model": session.model_id,
        "created_at": session.created_at.isoformat(),
    }


@router.get("/sessions", tags=["sessions"])
async def list_sessions(
    app: AtlasApplication = Depends(get_app),
    api_key: str = Depends(require_auth),
) -> dict[str, list[dict[str, Any]]]:
    """List all chat sessions."""
    manager = app.container.resolve("ai_manager")
    sessions = manager.list_sessions()
    
    return {
        "sessions": [
            {
                "session_id": s.session_id,
                "provider": s.provider_name,
                "model": s.model_id,
                "message_count": len(s.history),
                "created_at": s.created_at.isoformat(),
            }
            for s in sessions
        ],
    }


@router.get("/sessions/{session_id}", tags=["sessions"])
async def get_session(
    session_id: str,
    app: AtlasApplication = Depends(get_app),
    api_key: str = Depends(require_auth),
) -> dict[str, Any]:
    """Get session details."""
    manager = app.container.resolve("ai_manager")
    
    try:
        session = manager.get_session(session_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Session not found") from e
    
    return {
        "session_id": session.session_id,
        "provider": session.provider_name,
        "model": session.model_id,
        "system_prompt": session.system_prompt,
        "messages": [
            {"role": m.role.value, "content": m.content, "timestamp": m.timestamp.isoformat()}
            for m in session.history
        ],
    }


@router.delete("/sessions/{session_id}", tags=["sessions"])
async def delete_session(
    session_id: str,
    app: AtlasApplication = Depends(get_app),
    api_key: str = Depends(require_auth),
) -> dict[str, Any]:
    """Delete a chat session."""
    manager = app.container.resolve("ai_manager")
    
    try:
        manager.delete_session(session_id)
        return {"success": True, "message": "Session deleted"}
    except Exception as e:
        raise HTTPException(status_code=404, detail="Session not found") from e


# OpenAI-compatible endpoints
@openai_router.post("/chat/completions", response_model=None)
async def openai_chat_completions(
    request: Request,
    app: AtlasApplication = Depends(get_app),
    authorization: str = Depends(require_auth),
):
    """OpenAI-compatible chat completions endpoint."""
    import json
    
    body = await request.json()
    
    # Extract parameters
    model = body.get("model")
    messages = body.get("messages", [])
    temperature = body.get("temperature", 0.7)
    max_tokens = body.get("max_tokens", 1024)
    top_p = body.get("top_p", 0.95)
    stream = body.get("stream", False)
    
    if not model or not messages:
        raise HTTPException(status_code=400, detail="model and messages required")
    
    # Convert to internal format
    last_user_msg = None
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content")
            break
    
    if not last_user_msg:
        raise HTTPException(status_code=400, detail="No user message found")
    
    # Create session for this request
    manager = app.container.resolve("ai_manager")
    session = manager.new_session(
        provider_name=None,
        role=None,
        model_id=model,
        system_prompt="",
    )
    
    # Add conversation history
    for msg in messages[:-1]:  # Exclude last user message
        if msg.get("role") == "user":
            session.add_user_message(msg.get("content"))
        elif msg.get("role") == "assistant":
            session.add_assistant_message(msg.get("content"))
    
    # Execute
    try:
        if stream:
            async def generate() -> AsyncIterator[str]:
                async for chunk in manager.stream_chat(
                    session.session_id,
                    last_user_msg,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p,
                ):
                    chunk_data = {
                        "id": f"chatcmpl-{session.session_id[:8]}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": chunk},
                            "finish_reason": None,
                        }],
                    }
                    yield f"data: {json.dumps(chunk_data)}\n\n"
                yield "data: [DONE]\n\n"
            
            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
            )
        else:
            response = await manager.chat(
                session.session_id,
                last_user_msg,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
            )
            
            return {
                "id": f"chatcmpl-{session.session_id[:8]}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": response.message.content},
                    "finish_reason": "stop",
                }],
                "usage": {
                    "prompt_tokens": response.prompt_tokens,
                    "completion_tokens": response.completion_tokens,
                    "total_tokens": response.prompt_tokens + response.completion_tokens,
                },
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@openai_router.get("/models")
async def openai_list_models(
    app: AtlasApplication = Depends(get_app),
    authorization: str = Depends(require_auth),
) -> dict[str, Any]:
    """OpenAI-compatible models list."""
    manager = app.container.resolve("ai_manager")
    models = manager.list_models()
    
    return {
        "object": "list",
        "data": [
            {
                "id": m.model_id,
                "object": "model",
                "created": int(time.time()),
                "owned_by": m.provider_name,
            }
            for m in models
        ],
    }