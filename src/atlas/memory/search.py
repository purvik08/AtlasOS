"""Semantic search and reranking for Atlas OS memory system."""

from __future__ import annotations

import math
from typing import Any

# Optional import for loguru
try:
    from loguru import logger
    LOGURU_AVAILABLE = True
except ImportError:
    LOGURU_AVAILABLE = False
    import logging
    logger = logging.getLogger(__name__)

# Try to import cross-encoder for reranking
try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
except ImportError:
    CROSS_ENCODER_AVAILABLE = False
    CrossEncoder = None


class SemanticSearch:
    """Hybrid semantic search with vector + keyword (BM25) and reranking."""

    def __init__(
        self,
        embedding_manager: Any,
        store: Any,
        top_k: int = 5,
        rerank: bool = True,
        rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    ) -> None:
        self._embedding_manager = embedding_manager
        self._store = store
        self._top_k = top_k
        self._rerank = rerank
        self._rerank_model_name = rerank_model
        self._reranker = None
        self._bm25_index: dict[str, dict[str, int]] = {}
        self._doc_lengths: dict[str, int] = {}
        self._avg_doc_length = 0.0

    def _load_reranker(self) -> None:
        """Lazy load cross-encoder for reranking."""
        if self._reranker is None and CROSS_ENCODER_AVAILABLE:
            try:
                if LOGURU_AVAILABLE:
                    logger.info(f"Loading reranker: {self._rerank_model_name}")
                else:
                    logger.info(f"Loading reranker: {self._rerank_model_name}")
                self._reranker = CrossEncoder(self._rerank_model_name)
            except Exception as e:
                if LOGURU_AVAILABLE:
                    logger.warning(f"Failed to load reranker: {e}")
                else:
                    logger.warning(f"Failed to load reranker: {e}")
                self._reranker = None

    async def search_messages(
        self,
        query: str,
        conversation_id: str | None = None,
        top_k: int | None = None,
        min_score: float = 0.0,
        use_hybrid: bool = True,
    ) -> list[dict[str, Any]]:
        """Search messages by semantic similarity."""
        k = top_k or self._top_k

        # Generate query embedding
        query_embedding = self._embedding_manager.embed_single(query)

        # Vector search
        vector_results = await self._store.search_messages(
            query_embedding=query_embedding,
            conversation_id=conversation_id,
            limit=k * 2,  # Get more for reranking
            min_score=min_score,
        )

        if not vector_results:
            return []

        # Hybrid search: combine with BM25 if enabled
        if use_hybrid and self._bm25_index:
            bm25_scores = self._bm25_score(query, vector_results)
            for i, result in enumerate(vector_results):
                result["bm25_score"] = bm25_scores[i] if i < len(bm25_scores) else 0.0
                # Combine scores (simple weighted average)
                vector_score = 1.0 - result.get("_distance", 1.0)
                result["hybrid_score"] = 0.7 * vector_score + 0.3 * result["bm25_score"]
        else:
            for result in vector_results:
                result["hybrid_score"] = 1.0 - result.get("_distance", 1.0)

        # Sort by hybrid score
        vector_results.sort(key=lambda x: x.get("hybrid_score", 0), reverse=True)

        # Rerank if enabled
        if self._rerank and self._reranker:
            vector_results = await self._rerank_results(query, vector_results[:k])

        return vector_results[:k]

    async def search_documents(
        self,
        query: str,
        top_k: int | None = None,
        min_score: float = 0.0,
        filter_metadata: dict[str, Any] | None = None,
        use_hybrid: bool = True,
    ) -> list[dict[str, Any]]:
        """Search documents by semantic similarity."""
        k = top_k or self._top_k

        # Generate query embedding
        query_embedding = self._embedding_manager.embed_single(query)

        # Vector search
        vector_results = await self._store.search_documents(
            query_embedding=query_embedding,
            limit=k * 2,
            min_score=min_score,
            filter_metadata=filter_metadata,
        )

        if not vector_results:
            return []

        # Hybrid search
        if use_hybrid and self._bm25_index:
            bm25_scores = self._bm25_score(query, vector_results)
            for i, result in enumerate(vector_results):
                result["bm25_score"] = bm25_scores[i] if i < len(bm25_scores) else 0.0
                vector_score = 1.0 - result.get("_distance", 1.0)
                result["hybrid_score"] = 0.7 * vector_score + 0.3 * result["bm25_score"]
        else:
            for result in vector_results:
                result["hybrid_score"] = 1.0 - result.get("_distance", 1.0)

        # Sort by hybrid score
        vector_results.sort(key=lambda x: x.get("hybrid_score", 0), reverse=True)

        # Rerank
        if self._rerank and self._reranker:
            vector_results = await self._rerank_results(query, vector_results[:k])

        return vector_results[:k]

    def _bm25_score(self, query: str, results: list[dict[str, Any]]) -> list[float]:
        """Calculate BM25 scores for results."""
        if not self._bm25_index:
            return [0.0] * len(results)

        query_terms = query.lower().split()
        k1 = 1.5
        b = 0.75

        scores = []
        for result in results:
            content = result.get("content", "").lower()
            doc_id = result.get("id", "")
            doc_len = self._doc_lengths.get(doc_id, len(content.split()))

            score = 0.0
            for term in query_terms:
                # Term frequency in document
                tf = content.count(term)

                # Inverse document frequency
                df = len(self._bm25_index.get(term, {}))
                if df == 0:
                    continue
                N = len(self._doc_lengths)
                idf = math.log((N - df + 0.5) / (df + 0.5) + 1)

                # BM25 formula
                score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc_len / self._avg_doc_length))

            scores.append(score)

        # Normalize scores to [0, 1]
        if scores:
            max_score = max(scores) if max(scores) > 0 else 1
            scores = [s / max_score for s in scores]

        return scores

    async def _rerank_results(
        self,
        query: str,
        results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Rerank results using cross-encoder."""
        self._load_reranker()
        if not self._reranker or not results:
            return results

        try:
            pairs = [(query, result.get("content", "")) for result in results]
            scores = await asyncio.to_thread(self._reranker.predict, pairs)

            for result, score in zip(results, scores):
                result["rerank_score"] = float(score)

            # Sort by rerank score
            results.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
            return results
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.warning(f"Reranking failed: {e}")
            else:
                logger.warning(f"Reranking failed: {e}")
            return results

    def update_bm25_index(self, documents: list[dict[str, Any]]) -> None:
        """Update BM25 index with new documents."""
        self._bm25_index.clear()
        self._doc_lengths.clear()

        for doc in documents:
            doc_id = doc.get("id", "")
            content = doc.get("content", "").lower()
            terms = content.split()
            self._doc_lengths[doc_id] = len(terms)

            for term in set(terms):
                if term not in self._bm25_index:
                    self._bm25_index[term] = {}
                tf = terms.count(term)
                self._bm25_index[term][doc_id] = tf

        # Calculate average document length
        if self._doc_lengths:
            self._avg_doc_length = sum(self._doc_lengths.values()) / len(self._doc_lengths)

    def mmr_search(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        top_k: int | None = None,
        lambda_param: float = 0.5,
    ) -> list[dict[str, Any]]:
        """Maximal Marginal Relevance for diverse results."""
        k = top_k or self._top_k
        if not candidates:
            return []

        selected = []
        remaining = candidates.copy()

        # Start with highest scoring
        selected.append(remaining.pop(0))

        while len(selected) < k and remaining:
            best_idx = -1
            best_score = -1

            query_emb = self._embedding_manager.embed_single(query)

            for i, candidate in enumerate(remaining):
                cand_emb = candidate.get("embedding")
                if not cand_emb:
                    continue

                # Relevance to query
                relevance = self._cosine_similarity(query_emb, cand_emb)

                # Diversity: max similarity to already selected
                max_sim = 0
                for sel in selected:
                    sel_emb = sel.get("embedding")
                    if sel_emb:
                        sim = self._cosine_similarity(cand_emb, sel_emb)
                        max_sim = max(max_sim, sim)

                # MMR score
                mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = i

            if best_idx >= 0:
                selected.append(remaining.pop(best_idx))
            else:
                break

        return selected

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0

        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (norm_a * norm_b)


# Missing import
import asyncio

__all__ = ["SemanticSearch"]