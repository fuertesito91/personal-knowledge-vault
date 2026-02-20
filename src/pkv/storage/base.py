"""Abstract base class for vector stores and factory function."""

from abc import ABC, abstractmethod
from typing import Any


class VectorStoreBase(ABC):
    """Common interface for vector storage backends."""

    @abstractmethod
    def add_documents(
        self,
        collection_name: str,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """Add/upsert documents with embeddings."""

    @abstractmethod
    def query(
        self,
        collection_name: str,
        query_embedding: list[float],
        n_results: int = 10,
    ) -> dict[str, Any]:
        """Query by embedding. Returns dict with keys: ids, documents, metadatas, distances.
        Each value is a list of lists (outer list has one element for single query)."""

    @abstractmethod
    def get_all(self, collection_name: str = "documents") -> dict[str, Any]:
        """Get all documents and embeddings. Returns dict with: ids, documents, metadatas, embeddings."""

    @abstractmethod
    def count(self, collection_name: str = "documents") -> int:
        """Count documents in collection."""

    @abstractmethod
    def has_id(self, collection_name: str, doc_id: str) -> bool:
        """Check if a document ID exists."""

    @abstractmethod
    def get_or_create_collection(self, name: str = "documents") -> Any:
        """Get or create a collection. Returns a collection-like object."""

    @abstractmethod
    def get_by_ids(self, collection_name: str, ids: list[str], include: list[str] | None = None) -> dict[str, Any]:
        """Get documents by IDs. Returns dict with: ids, documents, metadatas, embeddings (based on include)."""

    @abstractmethod
    def delete_by_ids(self, collection_name: str, ids: list[str]) -> None:
        """Delete documents by IDs."""


def get_vector_store(config: dict[str, Any]) -> VectorStoreBase:
    """Factory: return the right vector store based on config."""
    backend = config.get("storage_backend", "chromadb")

    if backend == "bigquery":
        from .bigquery import BigQueryVectorStore
        bq_cfg = config.get("bigquery", {})
        return BigQueryVectorStore(
            project=bq_cfg.get("project", "ozpr-reporting-dev"),
            dataset=bq_cfg.get("dataset", "dbt_oriol"),
            table=bq_cfg.get("table", "pkv_oriol"),
        )
    elif backend == "chromadb":
        from .chromadb import ChromaVectorStore
        return ChromaVectorStore(config["chroma_path"])
    else:
        raise ValueError(f"Unknown storage_backend: {backend}")
