"""Tests for vault writer and ontology."""

import tempfile
from pathlib import Path

from pkv.vault.writer import VaultWriter
from pkv.vault.ontology import OntologyManager
from pkv.models import ProcessedDocument, Chunk


def _make_doc(title="Test", content="Hello world", hash_val="abc123"):
    return ProcessedDocument(
        title=title,
        content=content,
        chunks=[Chunk(content=content, index=0)],
        source_path="/tmp/test.md",
        source_type="markdown",
        content_hash=hash_val,
    )


def test_vault_writer():
    with tempfile.TemporaryDirectory() as tmpdir:
        writer = VaultWriter(tmpdir)
        doc = _make_doc()
        path = writer.write(doc)
        assert path is not None
        assert path.exists()
        assert path.read_text().startswith("---")


def test_vault_dedup():
    with tempfile.TemporaryDirectory() as tmpdir:
        writer = VaultWriter(tmpdir)
        doc = _make_doc()
        path1 = writer.write(doc)
        path2 = writer.write(doc)
        assert path1 is not None
        assert path2 is None  # duplicate


def test_ontology_extract_entities():
    om = OntologyManager()
    entities = om.extract_entities("I met John Smith at [[Project Alpha]] yesterday.")
    assert "Project Alpha" in entities
    assert "John Smith" in entities


def test_ontology_folders():
    om = OntologyManager()
    assert "people" in om.get_entity_folder("Person")
    assert "documents" == om.get_entity_folder("Document")
