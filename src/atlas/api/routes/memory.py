"""Memory store routes for Atlas OS API."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from atlas.api.auth import require_auth
from atlas.memory import MemoryService
from atlas.runtime.application import AtlasApplication

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["memory"])


class RememberRequest(BaseModel):
    text: str
    category: str = "general"
    source: str = "user"


class RecallRequest(BaseModel):
    query: str
    top_k: int = 10


def get_app(request: Request) -> AtlasApplication:
    return request.app.state.atlas_app


def get_memory_service(app: AtlasApplication) -> MemoryService:
    """Get or create singleton MemoryService tied to app data_dir."""
    if "memory_service" in app.container:
        return app.container.resolve("memory_service")
    data_dir = Path(getattr(app.config, "data_dir", "./data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    persist_path = data_dir / "memories.json"
    svc = MemoryService(persist_path=persist_path)
    app.container.register_instance("memory_service", svc)
    return svc


@router.get("/list")
async def list_memories(
    app: AtlasApplication = Depends(get_app),
    api_key: Any = Depends(require_auth),
) -> dict[str, Any]:
    """List all stored persistent memories."""
    svc = get_memory_service(app)
    entries = []
    if hasattr(svc, "_store") and hasattr(svc._store, "_entries"):
        for idx, entry in enumerate(svc._store._entries):
            meta = entry.metadata or {}
            entries.append({
                "id": meta.get("id", f"mem-{idx+1:03d}"),
                "text": entry.text,
                "category": meta.get("category", "general"),
                "timestamp": meta.get("timestamp", "Recent"),
                "source": meta.get("source", "system"),
            })
    return {
        "count": len(entries),
        "entries": entries,
    }


@router.post("/recall")
async def recall_memories(
    request: RecallRequest,
    app: AtlasApplication = Depends(get_app),
    api_key: Any = Depends(require_auth),
) -> dict[str, Any]:
    """Perform semantic vector search over memory store."""
    svc = get_memory_service(app)
    try:
        results = svc.recall(request.query, top_k=request.top_k)
        return {
            "query": request.query,
            "results": [
                {
                    "text": r.text,
                    "score": r.score,
                    "metadata": r.metadata,
                }
                for r in results
            ],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/remember")
async def remember_memory(
    request: RememberRequest,
    app: AtlasApplication = Depends(get_app),
    api_key: Any = Depends(require_auth),
) -> dict[str, Any]:
    """Store a new memory in persistent vector store."""
    import uuid
    from datetime import datetime

    svc = get_memory_service(app)
    mem_id = f"mem-{uuid.uuid4().hex[:6]}"
    now_str = datetime.now().strftime("%b %d, %H:%M")

    try:
        svc.remember(
            request.text,
            metadata={
                "id": mem_id,
                "category": request.category,
                "timestamp": now_str,
                "source": request.source,
            },
        )
        return {
            "success": True,
            "id": mem_id,
            "text": request.text,
            "category": request.category,
            "timestamp": now_str,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    app: AtlasApplication = Depends(get_app),
    api_key: Any = Depends(require_auth),
) -> dict[str, Any]:
    """Delete a memory entry by ID."""
    svc = get_memory_service(app)
    try:
        if hasattr(svc, "_store") and hasattr(svc._store, "_entries"):
            svc._store._entries = [
                e for e in svc._store._entries
                if (e.metadata or {}).get("id") != memory_id
            ]
            svc._store.save()
        return {"success": True, "message": f"Memory '{memory_id}' deleted."}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
