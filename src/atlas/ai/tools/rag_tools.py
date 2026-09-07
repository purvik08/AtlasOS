"""RAG knowledge base tools for Atlas OS AI."""

from __future__ import annotations

import logging
from typing import Any

from atlas.ai.tools.base import BaseTool, ToolParameter, ToolPermissionLevel, ToolResult
from atlas.rag.service import RAGService

logger = logging.getLogger(__name__)


class SearchKnowledgeTool(BaseTool):
    """Tool to search user documents and knowledge base for answers."""

    name = "search_knowledge"
    description = "Search documents, knowledge base, notes, and manuals ingested into the RAG subsystem."
    permission_level = ToolPermissionLevel.READ_ONLY
    parameters = [
        ToolParameter(
            name="query",
            param_type="string",
            description="The search query or topic to look up in the knowledge base",
            required=True,
        ),
        ToolParameter(
            name="top_k",
            param_type="integer",
            description="Number of relevant snippets to retrieve (default: 3)",
            required=False,
            default=3,
        ),
    ]

    def __init__(self, rag_service: RAGService | None = None) -> None:
        self._rag_service = rag_service

    async def execute(self, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query", "")
        top_k = int(kwargs.get("top_k", 3))
        try:
            svc = self._rag_service or RAGService()
            results = svc.search(query=query, top_k=top_k)
            data = [r.to_dict() for r in results]
            return ToolResult(success=True, data=data)
        except Exception as exc:
            return ToolResult(success=False, data=None, error=str(exc))


class ListKnowledgeDocumentsTool(BaseTool):
    """Tool to list indexed documents in the knowledge base."""

    name = "list_knowledge_documents"
    description = "List all documents and files currently ingested into the RAG knowledge base."
    permission_level = ToolPermissionLevel.READ_ONLY
    parameters = []

    def __init__(self, rag_service: RAGService | None = None) -> None:
        self._rag_service = rag_service

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            svc = self._rag_service or RAGService()
            docs = svc.list_documents()
            data = [d.to_dict() for d in docs]
            return ToolResult(success=True, data=data)
        except Exception as exc:
            return ToolResult(success=False, data=None, error=str(exc))
