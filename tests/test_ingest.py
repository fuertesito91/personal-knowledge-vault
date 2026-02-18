"""Tests for the ingestion pipeline."""

import tempfile
from pathlib import Path

from pkv.ingest.processor import process_file, compute_hash
from pkv.ingest.chunker import chunk_text, estimate_tokens
from pkv.config import DEFAULT_CONFIG


def test_compute_hash():
    assert compute_hash("hello") == compute_hash("hello")
    assert compute_hash("hello") != compute_hash("world")


def test_estimate_tokens():
    assert estimate_tokens("hello world") > 0
    assert estimate_tokens("a" * 400) == 100


def test_chunk_short_text():
    chunks = chunk_text("Short text.", max_tokens=500)
    assert len(chunks) == 1
    assert chunks[0] == "Short text."


def test_chunk_long_text():
    text = "\n\n".join([f"Paragraph {i}. " * 20 for i in range(10)])
    chunks = chunk_text(text, max_tokens=100, overlap_tokens=0)
    assert len(chunks) > 1


def test_process_markdown():
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
        f.write("---\ntitle: Test Doc\ntags: [test]\n---\n# Hello\n\nThis is a test document.")
        f.flush()
        doc = process_file(Path(f.name), DEFAULT_CONFIG)
        assert doc is not None
        assert doc.title == "Test Doc"
        assert doc.source_type == "markdown"
        assert len(doc.chunks) >= 1


def test_process_text():
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
        f.write("Hello world\nThis is plain text content.")
        f.flush()
        doc = process_file(Path(f.name), DEFAULT_CONFIG)
        assert doc is not None
        assert doc.source_type == "text"


def test_process_json():
    import json
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump({"key": "value", "nested": {"a": 1}}, f)
        f.flush()
        doc = process_file(Path(f.name), DEFAULT_CONFIG)
        assert doc is not None
        assert doc.source_type == "json"


def test_unsupported_format():
    with tempfile.NamedTemporaryFile(suffix=".xyz", mode="w", delete=False) as f:
        f.write("unsupported")
        f.flush()
        doc = process_file(Path(f.name), DEFAULT_CONFIG)
        assert doc is None


def test_idempotent_hashing():
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
        f.write("# Same content")
        f.flush()
        doc1 = process_file(Path(f.name), DEFAULT_CONFIG)
        doc2 = process_file(Path(f.name), DEFAULT_CONFIG)
        assert doc1.content_hash == doc2.content_hash
