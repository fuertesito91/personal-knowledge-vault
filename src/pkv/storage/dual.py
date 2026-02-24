"""Dual vector store — writes to both ChromaDB and BigQuery, reads from ChromaDB.

Keeps both backends in sync automatically. ChromaDB is the primary (fast local reads),
BigQuery is the cloud mirror (remote access, analytics).
"""

import logging
from typing import Any

import numpy as np

from .base import VectorStoreBase

logger = logging.getLogger(__name__)


def _to_lists(embeddings: list) -> list[list[float]]:
    """Convert numpy arrays to plain lists for JSON serialization."""
    return [e.tolist() if isinstance(e, np.ndarray) else list(e) for e in embeddings]


class DualVectorStore(VectorStoreBase):
    """Writes to both ChromaDB and BigQuery; reads from ChromaDB (primary)."""

    def __init__(self, primary: VectorStoreBase, secondary: VectorStoreBase):
        self.primary = primary
        self.secondary = secondary

    def get_or_create_collection(self, name: str = "documents") -> Any:
        self.secondary.get_or_create_collection(name)
        return self.primary.get_or_create_collection(name)

    def add_documents(
        self,
        collection_name: str,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        # Write to primary first
        self.primary.add_documents(collection_name, ids, embeddings, documents, metadatas)
        # Then mirror to secondary
        try:
            self.secondary.add_documents(collection_name, ids, _to_lists(embeddings), documents, metadatas)
        except Exception as e:
            logger.warning(f"Secondary store write failed (will retry on next sync): {e}")

    def query(
        self,
        collection_name: str,
        query_embedding: list[float],
        n_results: int = 10,
    ) -> dict[str, Any]:
        return self.primary.query(collection_name, query_embedding, n_results)

    def get_all(self, collection_name: str = "documents") -> dict[str, Any]:
        return self.primary.get_all(collection_name)

    def count(self, collection_name: str = "documents") -> int:
        return self.primary.count(collection_name)

    def has_id(self, collection_name: str, doc_id: str) -> bool:
        return self.primary.has_id(collection_name, doc_id)

    def get_by_ids(self, collection_name: str, ids: list[str], include: list[str] | None = None) -> dict[str, Any]:
        return self.primary.get_by_ids(collection_name, ids, include)

    def delete_by_ids(self, collection_name: str, ids: list[str]) -> None:
        self.primary.delete_by_ids(collection_name, ids)
        try:
            self.secondary.delete_by_ids(collection_name, ids)
        except Exception as e:
            logger.warning(f"Secondary store delete failed: {e}")
