"""Unit tests for MemoryService and MemoryStore."""

from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

import pytest

from atlas.memory.embedder import HashEmbedder
from atlas.memory.service import MemoryService
from atlas.memory.store import MemoryEntry, MemoryResult, MemoryStore, _cosine_similarity


class TestCosineSimiliarity:
    def test_identical_vectors(self):
        v = [1.0, 0.0, 0.0]
        assert abs(_cosine_similarity(v, v) - 1.0) < 1e-9

    def test_orthogonal_vectors(self):
        assert abs(_cosine_similarity([1.0, 0.0], [0.0, 1.0])) < 1e-9

    def test_opposite_vectors(self):
        assert abs(_cosine_similarity([1.0, 0.0], [-1.0, 0.0]) - (-1.0)) < 1e-9

    def test_zero_vector(self):
        assert _cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


class TestMemoryStore:
    def test_add_and_len(self):
        store = MemoryStore()
        store.add(MemoryEntry("text", [1.0, 0.0], {}))
        assert len(store) == 1

    def test_search_returns_most_similar(self):
        store = MemoryStore()
        store.add(MemoryEntry("text_a", [1.0, 0.0], {"id": "a"}))
        store.add(MemoryEntry("text_b", [0.0, 1.0], {"id": "b"}))

        # Query close to text_a
        results = store.search([1.0, 0.0], top_k=2)
        assert results[0].metadata["id"] == "a"

    def test_search_top_k_limits_results(self):
        store = MemoryStore()
        for i in range(10):
            store.add(MemoryEntry(f"text_{i}", [float(i), 0.0], {}))
        results = store.search([9.0, 0.0], top_k=3)
        assert len(results) <= 3

    def test_search_threshold_filters_results(self):
        store = MemoryStore()
        store.add(MemoryEntry("match", [1.0, 0.0], {}))
        store.add(MemoryEntry("no-match", [0.0, 1.0], {}))
        # Threshold 0.99 — only near-identical match should pass
        results = store.search([1.0, 0.0], threshold=0.99)
        assert len(results) == 1
        assert results[0].text == "match"

    def test_search_empty_store(self):
        store = MemoryStore()
        results = store.search([1.0, 0.0])
        assert results == []

    def test_clear(self):
        store = MemoryStore()
        store.add(MemoryEntry("text", [1.0, 0.0], {}))
        store.clear()
        assert len(store) == 0

    def test_persistence_round_trip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "store.json"
            store1 = MemoryStore(persist_path=path)
            store1.add(MemoryEntry("hello", [0.5, 0.5], {"tag": "greeting"}))
            store1.save()

            store2 = MemoryStore(persist_path=path)
            assert len(store2) == 1
            assert store2._entries[0].text == "hello"
            assert store2._entries[0].metadata["tag"] == "greeting"

    def test_search_result_has_score(self):
        store = MemoryStore()
        store.add(MemoryEntry("exact", [1.0, 0.0], {}))
        results = store.search([1.0, 0.0])
        assert results[0].score > 0.99

    def test_search_sorted_by_score(self):
        store = MemoryStore()
        store.add(MemoryEntry("low",  [0.0, 1.0], {}))
        store.add(MemoryEntry("high", [1.0, 0.0], {}))
        results = store.search([1.0, 0.0])
        assert results[0].score >= results[-1].score


class TestMemoryService:
    """Tests for MemoryService using HashEmbedder (no ML deps needed)."""

    def make_service(self, persist_path=None):
        return MemoryService(embedder=HashEmbedder(), persist_path=persist_path)

    def test_remember_increases_count(self):
        svc = self.make_service()
        assert svc.entry_count == 0
        svc.remember("the sky is blue")
        assert svc.entry_count == 1

    def test_recall_returns_results(self):
        svc = self.make_service()
        svc.remember("the sky is blue")
        svc.remember("cats like fish")
        results = svc.recall("sky colour")
        assert len(results) > 0
        assert all(isinstance(r, MemoryResult) for r in results)

    def test_recall_top_k_respected(self):
        svc = self.make_service()
        for i in range(10):
            svc.remember(f"fact number {i}")
        results = svc.recall("some query", top_k=3)
        assert len(results) <= 3

    def test_clear_resets_count(self):
        svc = self.make_service()
        svc.remember("something")
        svc.clear()
        assert svc.entry_count == 0

    def test_remember_batch(self):
        svc = self.make_service()
        svc.remember_batch(["alpha", "beta", "gamma"])
        assert svc.entry_count == 3

    def test_remember_with_metadata(self):
        svc = self.make_service()
        svc.remember("user likes dark mode", metadata={"source": "prefs"})
        results = svc.recall("dark mode preference")
        assert results[0].metadata.get("source") == "prefs"

    def test_status_dict(self):
        svc = self.make_service()
        s = svc.status()
        assert "embedder" in s
        assert "entry_count" in s
        assert "hash_fallback" in s
        # With HashEmbedder, hash_fallback should be True
        assert s["hash_fallback"] is True

    def test_embedder_name_property(self):
        svc = self.make_service()
        assert svc.embedder_name == "HashEmbedder"

    def test_embedder_dimension_property(self):
        svc = self.make_service()
        assert svc.embedder_dimension == 128

    def test_persistence_across_instances(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mem.json"
            svc1 = self.make_service(persist_path=path)
            svc1.remember("persisted fact")

            svc2 = self.make_service(persist_path=path)
            assert svc2.entry_count == 1
