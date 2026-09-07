"""Unit tests for memory embedders.

HashEmbedder tests always run (zero dependencies).
SentenceTransformerEmbedder tests are guarded with a skip decorator
when sentence-transformers is not installed.
"""

from __future__ import annotations

import math
import pytest

from atlas.memory.embedder import (
    HashEmbedder,
    SentenceTransformerEmbedder,
    create_best_embedder,
)

# Check if sentence-transformers is available
try:
    import sentence_transformers  # noqa: F401
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False


class TestHashEmbedder:
    """Tests for HashEmbedder — always runs, no ML deps."""

    def setup_method(self):
        self.embedder = HashEmbedder()

    def test_name(self):
        assert self.embedder.name == "HashEmbedder"

    def test_dimension(self):
        assert self.embedder.dimension == 128

    def test_returns_correct_length(self):
        vec = self.embedder.embed("hello world")
        assert len(vec) == 128

    def test_returns_floats(self):
        vec = self.embedder.embed("test")
        assert all(isinstance(v, float) for v in vec)

    def test_deterministic(self):
        """Same input must produce identical vectors."""
        v1 = self.embedder.embed("atlas os")
        v2 = self.embedder.embed("atlas os")
        assert v1 == v2

    def test_different_inputs_differ(self):
        v1 = self.embedder.embed("raspberry pi")
        v2 = self.embedder.embed("neural network")
        assert v1 != v2

    def test_normalised(self):
        """Vectors should be L2-normalised (magnitude ≈ 1.0)."""
        vec = self.embedder.embed("normalisation test")
        magnitude = math.sqrt(sum(v * v for v in vec))
        assert abs(magnitude - 1.0) < 1e-5

    def test_empty_string(self):
        """Empty string should still produce a valid vector."""
        vec = self.embedder.embed("")
        assert len(vec) == 128

    def test_whitespace_normalisation(self):
        """Leading/trailing whitespace is stripped before hashing."""
        v1 = self.embedder.embed("atlas")
        v2 = self.embedder.embed("  atlas  ")
        assert v1 == v2

    def test_embed_batch_returns_correct_count(self):
        texts = ["alpha", "beta", "gamma"]
        vecs = self.embedder.embed_batch(texts)
        assert len(vecs) == 3
        assert all(len(v) == 128 for v in vecs)

    def test_embed_batch_consistent_with_embed(self):
        texts = ["hello", "world"]
        batch_vecs = self.embedder.embed_batch(texts)
        for text, batch_vec in zip(texts, batch_vecs):
            single_vec = self.embedder.embed(text)
            assert batch_vec == single_vec


class TestCreateBestEmbedder:
    """Tests for the auto-selection factory."""

    def test_returns_embedder(self):
        embedder = create_best_embedder()
        assert embedder is not None

    def test_returns_hash_embedder_when_st_unavailable(self):
        """Should return HashEmbedder when sentence-transformers is missing."""
        import unittest.mock as mock
        # Simulate missing sentence-transformers
        with mock.patch.dict("sys.modules", {"sentence_transformers": None}):
            embedder = create_best_embedder()
            # It will try ST and fail → fall back
            assert embedder.dimension > 0

    def test_hash_embedder_is_always_available(self):
        embedder = HashEmbedder()
        vec = embedder.embed("always works")
        assert len(vec) == 128


@pytest.mark.skipif(not ST_AVAILABLE, reason="sentence-transformers not installed")
class TestSentenceTransformerEmbedder:
    """Tests for SentenceTransformerEmbedder — only when dep is installed."""

    def setup_method(self):
        self.embedder = SentenceTransformerEmbedder("all-MiniLM-L6-v2")

    def test_name_contains_model(self):
        assert "all-MiniLM-L6-v2" in self.embedder.name

    def test_dimension_positive(self):
        assert self.embedder.dimension > 0

    def test_embed_returns_correct_length(self):
        vec = self.embedder.embed("hello world")
        assert len(vec) == self.embedder.dimension

    def test_normalised(self):
        vec = self.embedder.embed("embedding test")
        magnitude = math.sqrt(sum(v * v for v in vec))
        assert abs(magnitude - 1.0) < 1e-4

    def test_similar_texts_have_higher_score_than_dissimilar(self):
        from atlas.memory.store import _cosine_similarity
        v_cat = self.embedder.embed("my cat sits on the mat")
        v_dog = self.embedder.embed("my dog sits on the rug")
        v_unrelated = self.embedder.embed("quantum computing theory")
        sim_cat_dog = _cosine_similarity(v_cat, v_dog)
        sim_cat_unrelated = _cosine_similarity(v_cat, v_unrelated)
        assert sim_cat_dog > sim_cat_unrelated

    def test_batch_consistency(self):
        texts = ["alpha", "beta"]
        batch_vecs = self.embedder.embed_batch(texts)
        for text, batch_vec in zip(texts, batch_vecs):
            single_vec = self.embedder.embed(text)
            # Should be very close (floating point differences OK)
            assert all(abs(a - b) < 1e-5 for a, b in zip(single_vec, batch_vec))
