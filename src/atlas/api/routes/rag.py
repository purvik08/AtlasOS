"""RAG subsystem routes for Atlas OS API."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from atlas.api.auth import require_auth
from atlas.rag.service import RAGService
from atlas.runtime.application import AtlasApplication

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["rag"])


class RAGIngestRequest(BaseModel):
    """Request to ingest file or raw text into RAG knowledge base."""
    file_path: str | None = None
    text: str | None = None
    title: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RAGQueryRequest(BaseModel):
    """Semantic query request for RAG retrieval."""
    query: str
    top_k: int = Field(default=3, ge=1, le=20)
    threshold: float = Field(default=0.0, ge=0.0, le=1.0)


def get_app(request: Request) -> AtlasApplication:
    return request.app.state.atlas_app


def get_rag_service(app: AtlasApplication = Depends(get_app)) -> RAGService:
    if "rag_service" in app.container:
        return app.container.resolve("rag_service")
    # Initialize and register if not present
    rag_svc = RAGService(data_dir=getattr(app.config, "data_dir", "./data"))
    app.container.register_instance("rag_service", rag_svc)
    return rag_svc


@router.post("/ingest")
async def ingest_document(
    request: RAGIngestRequest,
    rag_svc: RAGService = Depends(get_rag_service),
    api_key: Any = Depends(require_auth),
) -> dict[str, Any]:
    """Ingest a file or text snippet into the RAG knowledge base."""
    if request.file_path:
        res = rag_svc.ingest_file(
            file_path=request.file_path,
            title=request.title,
            metadata=request.metadata,
        )
    elif request.text:
        res = rag_svc.ingest_text(
            text=request.text,
            title=request.title or "Text Snippet",
            metadata=request.metadata,
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Either 'file_path' or 'text' must be provided for ingestion.",
        )

    if not res.success:
        raise HTTPException(status_code=400, detail=res.error or "Ingestion failed.")

    return res.to_dict()


@router.post("/query")
async def query_knowledge(
    request: RAGQueryRequest,
    rag_svc: RAGService = Depends(get_rag_service),
    api_key: Any = Depends(require_auth),
) -> dict[str, Any]:
    """Search knowledge chunks by query and return formatted citations."""
    results = rag_svc.search(
        query=request.query,
        top_k=request.top_k,
        threshold=request.threshold,
    )
    context_text = rag_svc.build_rag_context(
        query=request.query,
        top_k=request.top_k,
        threshold=request.threshold,
    )
    return {
        "query": request.query,
        "results_count": len(results),
        "results": [r.to_dict() for r in results],
        "context": context_text,
    }


@router.get("/documents")
async def list_documents(
    rag_svc: RAGService = Depends(get_rag_service),
    api_key: Any = Depends(require_auth),
) -> dict[str, Any]:
    """List all indexed documents in the RAG knowledge base."""
    docs = rag_svc.list_documents()
    return {
        "count": len(docs),
        "documents": [d.to_dict() for d in docs],
    }


@router.get("/documents/{doc_id}")
async def get_document_details(
    doc_id: str,
    rag_svc: RAGService = Depends(get_rag_service),
    api_key: Any = Depends(require_auth),
) -> dict[str, Any]:
    """Get metadata for a specific indexed document."""
    doc = rag_svc.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    return doc.to_dict()


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    rag_svc: RAGService = Depends(get_rag_service),
    api_key: Any = Depends(require_auth),
) -> dict[str, Any]:
    """Remove a document and its embeddings from the RAG knowledge base."""
    ok = rag_svc.delete_document(doc_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    return {"success": True, "doc_id": doc_id, "message": "Document deleted."}


@router.post("/clear")
async def clear_rag_index(
    rag_svc: RAGService = Depends(get_rag_service),
    api_key: Any = Depends(require_auth),
) -> dict[str, Any]:
    """Clear all indexed documents and embeddings."""
    rag_svc.clear()
    return {"success": True, "message": "RAG knowledge base cleared."}
