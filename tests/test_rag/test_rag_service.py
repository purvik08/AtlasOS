"""Tests for Atlas OS RAG subsystem."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from atlas.rag.document import DocumentChunker, TextExtractor
from atlas.rag.service import RAGService


def test_chunker_basic():
    chunker = DocumentChunker(chunk_size=100, chunk_overlap=20)
    text = "Hello world.\n\nThis is paragraph two of the document.\n\nAnd paragraph three."
    chunks = chunker.chunk_text(text, doc_id="doc_1", doc_title="Test Doc")
    assert len(chunks) >= 1
    assert chunks[0].doc_id == "doc_1"
    assert chunks[0].doc_title == "Test Doc"
    assert chunks[0].total_chunks == len(chunks)


def test_text_extractor(tmp_path):
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text("Atlas OS notes content", encoding="utf-8")

    text, title, mime = TextExtractor.extract(txt_file)
    assert text == "Atlas OS notes content"
    assert title == "Notes"
    assert "text" in mime


def test_rag_service_lifecycle(tmp_path):
    rag_dir = tmp_path / "rag_data"
    service = RAGService(data_dir=rag_dir, chunk_size=200, chunk_overlap=20)

    # Ingest text
    res = service.ingest_text(
        text="Atlas OS is an AI-driven operating system designed for edge devices and Raspberry Pi 5.",
        title="Atlas OS Overview",
    )
    assert res.success is True
    assert res.chunk_count >= 1

    # Search
    results = service.search("Raspberry Pi edge", top_k=2)
    assert len(results) >= 1
    assert "Atlas OS" in results[0].text

    # Build context
    ctx = service.build_rag_context("Raspberry Pi")
    assert "Atlas OS Overview" in ctx

    # List
    docs = service.list_documents()
    assert len(docs) == 1
    assert docs[0].title == "Atlas OS Overview"

    # Delete
    ok = service.delete_document(res.doc_id)
    assert ok is True
    assert len(service.list_documents()) == 0
