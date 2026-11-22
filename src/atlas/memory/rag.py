"""RAG pipeline for Atlas OS memory system."""

from __future__ import annotations

from typing import Any

# Optional import for loguru
try:
    from loguru import logger
    LOGURU_AVAILABLE = True
except ImportError:
    LOGURU_AVAILABLE = False
    import logging
    logger = logging.getLogger(__name__)

from .models import Document, SearchResult
from .store import LanceDBStore
from .embeddings import EmbeddingManager
from .search import SemanticSearch


class RAGPipeline:
    """Retrieval-Augmented Generation pipeline."""

    def __init__(
        self,
        store: LanceDBStore,
        embedding_manager: EmbeddingManager,
        search: SemanticSearch,
        max_context_tokens: int = 4000,
        top_k: int = 5,
        min_score: float = 0.3,
    ) -> None:
        self._store = store
        self._embedding_manager = embedding_manager
        self._search = search
        self._max_context_tokens = max_context_tokens
        self._top_k = top_k
        self._min_score = min_score

    async def query(
        self,
        query: str,
        conversation_id: str | None = None,
        include_conversation_context: bool = True,
        top_k: int | None = None,
        min_score: float | None = None,
    ) -> dict[str, Any]:
        """
        Execute RAG query: retrieve relevant documents and conversation history,
        then return context for generation.
        """
        k = top_k or self._top_k
        score_threshold = min_score if min_score is not None else self._min_score

        # Search documents
        doc_results = await self._search.search_documents(
            query=query,
            top_k=k,
            min_score=score_threshold,
        )

        # Search conversation if provided
        conv_results = []
        if conversation_id and include_conversation_context:
            conv_results = await self._search.search_messages(
                query=query,
                conversation_id=conversation_id,
                top_k=k // 2,
                min_score=score_threshold,
            )

        # Combine and deduplicate
        all_results = self._combine_results(doc_results, conv_results)

        # Apply MMR for diversity
        diverse_results = self._search.mmr_search(
            query=query,
            candidates=all_results,
            top_k=k,
        )

        # Build context
        context = self._build_context(diverse_results)

        return {
            "query": query,
            "results": [
                SearchResult(
                    id=r["id"],
                    content=r["content"],
                    score=r.get("hybrid_score", r.get("rerank_score", 0)),
                    metadata=r.get("metadata", {}),
                    conversation_id=r.get("conversation_id"),
                    message_id=r.get("message_id"),
                )
                for r in diverse_results
            ],
            "context": context,
            "context_tokens": self._estimate_tokens(context),
        }

    def _combine_results(
        self,
        doc_results: list[dict[str, Any]],
        conv_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Combine and deduplicate results."""
        seen = set()
        combined = []

        for result in doc_results + conv_results:
            doc_id = result.get("id", "")
            if doc_id and doc_id not in seen:
                seen.add(doc_id)
                combined.append(result)

        return combined

    def _build_context(self, results: list[dict[str, Any]]) -> str:
        """Build context string from search results."""
        if not results:
            return ""

        context_parts = []
        total_tokens = 0

        for result in results:
            content = result.get("content", "")
            score = result.get("hybrid_score", result.get("rerank_score", 0))
            metadata = result.get("metadata", {})

            # Estimate tokens
            tokens = len(content) // 4
            if total_tokens + tokens > self._max_context_tokens:
                break

            # Format context entry
            source = metadata.get("source", "document")
            if "conversation_id" in result:
                source = f"conversation ({result['conversation_id'][:8]})"

            entry = f"[Source: {source}, Score: {score:.3f}]\n{content}"
            context_parts.append(entry)
            total_tokens += tokens

        return "\n\n---\n\n".join(context_parts)

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation."""
        return len(text) // 4

    async def ingest_document(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
    ) -> list[Document]:
        """
        Ingest a document by chunking and embedding.
        Returns list of created document chunks.
        """
        chunks = self._chunk_text(content, chunk_size, chunk_overlap)
        documents = []

        for i, chunk in enumerate(chunks):
            chunk_metadata = (metadata or {}).copy()
            chunk_metadata.update({
                "chunk_index": i,
                "total_chunks": len(chunks),
                "source": metadata.get("source", "unknown") if metadata else "unknown",
            })

            embedding = self._embedding_manager.embed_single(chunk)

            document = Document(
                content=chunk,
                embedding=embedding,
                metadata=chunk_metadata,
            )

            await self._store.add_document(document)
            documents.append(document)

        if LOGURU_AVAILABLE:
            logger.info(f"Ingested document: {len(chunks)} chunks")
        else:
            logger.info(f"Ingested document: {len(chunks)} chunks")

        return documents

    def _chunk_text(self, text: str, chunk_size: int, overlap: int) -> list[str]:
        """Split text into overlapping chunks."""
        words = text.split()
        if len(words) <= chunk_size:
            return [text]

        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            if chunk:
                chunks.append(chunk)
            if i + chunk_size >= len(words):
                break

        return chunks

    async def stream_query(
        self,
        query: str,
        conversation_id: str | None = None,
        **kwargs,
    ):
        """
        Stream RAG query results (for future streaming generation integration).
        Currently yields the context for the generator to use.
        """
        result = await self.query(query, conversation_id, **kwargs)
        yield {
            "type": "context",
            "data": result,
        }


__all__ = ["RAGPipeline"]