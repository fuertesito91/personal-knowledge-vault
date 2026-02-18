"""ChromaDB wrapper for persistent vector storage."""

from pathlib import Path
from typing import Any

import chromadb


class VectorStore:
    """ChromaDB-backed persistent vector store."""

    def __init__(self, chroma_path: str):
        self.chroma_path = Path(chroma_path)
        self.chroma_path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.chroma_path))

    def get_or_create_collection(self, name: str = "documents") -> chromadb.Collection:
        """Get or create a ChromaDB collection."""
        return self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_documents(
        self,
        collection_name: str,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """Add documents to a collection."""
        collection = self.get_or_create_collection(collection_name)
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def query(
        self,
        collection_name: str,
        query_embedding: list[float],
        n_results: int = 10,
    ) -> dict[str, Any]:
        """Query a collection by embedding."""
        collection = self.get_or_create_collection(collection_name)
        return collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

    def get_all(self, collection_name: str = "documents") -> dict[str, Any]:
        """Get all documents and embeddings from a collection."""
        collection = self.get_or_create_collection(collection_name)
        return collection.get(include=["documents", "metadatas", "embeddings"])

    def count(self, collection_name: str = "documents") -> int:
        """Count documents in a collection."""
        collection = self.get_or_create_collection(collection_name)
        return collection.count()

    def has_id(self, collection_name: str, doc_id: str) -> bool:
        """Check if a document ID exists in a collection."""
        collection = self.get_or_create_collection(collection_name)
        result = collection.get(ids=[doc_id])
        return len(result["ids"]) > 0
