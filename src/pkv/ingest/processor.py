"""Universal document processor - the heart of ingestion."""

import hashlib
from pathlib import Path
from typing import Any

from ..models import Chunk, ProcessedDocument
from .chunker import chunk_text
from .parsers import PARSERS


def compute_hash(content: str) -> str:
    """SHA256 hash of content for dedup."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def process_file(file_path: Path, config: dict[str, Any]) -> ProcessedDocument | None:
    """Process a single file into a ProcessedDocument.

    Args:
        file_path: Path to the file to process.
        config: Application configuration dict.

    Returns:
        ProcessedDocument or None if file type is unsupported.
    """
    ext = file_path.suffix.lower()
    parser_cls = PARSERS.get(ext)
    if parser_cls is None:
        return None

    parser = parser_cls()
    result = parser.parse(file_path)

    content = result["content"]
    metadata = result.get("metadata", {})
    title = result.get("title", file_path.stem)
    content_hash = compute_hash(content)

    # Determine entity type from source_type
    source_type = metadata.get("source_type", "text")
    entity_type = _infer_entity_type(source_type, metadata)

    # Chunk
    chunk_cfg = config.get("chunking", {})
    text_chunks = chunk_text(
        content,
        max_tokens=chunk_cfg.get("max_tokens", 500),
        overlap_tokens=chunk_cfg.get("overlap_tokens", 50),
        respect_boundaries=chunk_cfg.get("respect_boundaries", True),
    )

    chunks = [
        Chunk(content=c, index=i, metadata={"source": str(file_path), "title": title})
        for i, c in enumerate(text_chunks)
    ]

    return ProcessedDocument(
        title=title,
        content=content,
        chunks=chunks,
        source_path=str(file_path),
        source_type=source_type,
        content_hash=content_hash,
        metadata=metadata,
        entity_type=entity_type,
        tags=metadata.get("tags", []),
    )


def process_directory(ingest_path: Path, config: dict[str, Any]) -> list[ProcessedDocument]:
    """Process all files in a directory."""
    docs = []
    if not ingest_path.exists():
        return docs

    for file_path in sorted(ingest_path.rglob("*")):
        if file_path.is_file() and not file_path.name.startswith("."):
            doc = process_file(file_path, config)
            if doc:
                docs.append(doc)
    return docs


def _infer_entity_type(source_type: str, metadata: dict) -> str:
    """Infer the ontology entity type from source metadata."""
    if source_type == "conversation":
        return "Conversation"
    if source_type == "pdf":
        return "Document"
    if source_type == "docx":
        return "Document"
    if "meeting" in metadata.get("title", "").lower():
        return "Meeting"
    return "Document"
