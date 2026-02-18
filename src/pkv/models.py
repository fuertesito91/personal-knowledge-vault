"""Data models used throughout PKV."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Chunk:
    """A chunk of text from a document."""
    content: str
    index: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessedDocument:
    """A fully processed document ready for the vault."""
    title: str
    content: str
    chunks: list[Chunk]
    source_path: str
    source_type: str  # e.g., "markdown", "pdf", "conversation"
    content_hash: str
    metadata: dict[str, Any] = field(default_factory=dict)
    entity_type: str = "Document"
    date: str = field(default_factory=lambda: datetime.now().isoformat()[:10])
    tags: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)


@dataclass
class ClusterResult:
    """Result of clustering."""
    cluster_id: int
    document_ids: list[str]
    centroid: list[float] | None = None
    label: str = ""


@dataclass
class Relationship:
    """A scored relationship between two documents."""
    doc_a: str
    doc_b: str
    score: float
    cluster_id: int = -1
    label: str = ""
