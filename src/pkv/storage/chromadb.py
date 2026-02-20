"""ChromaDB vector store backend — wraps the existing store.py logic."""

from pathlib import Path
from typing import Any

import chromadb

from .base import VectorStoreBase


class ChromaVectorStore(VectorStoreBase):
    """ChromaDB-backed persistent vector store."""

    def __init__(self, chroma_path: str):
        self.chroma_path = Path(chroma_path)
        self.chroma_path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.chroma_path))

    def get_or_create_collection(self, name: str = "documents") -> chromadb.Collection:
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
        collection = self.get_or_create_collection(collection_name)
        collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)

    def query(
        self,
        collection_name: str,
        query_embedding: list[float],
        n_results: int = 10,
    ) -> dict[str, Any]:
        collection = self.get_or_create_collection(collection_name)
        return collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

    def get_all(self, collection_name: str = "documents") -> dict[str, Any]:
        collection = self.get_or_create_collection(collection_name)
        return collection.get(include=["documents", "metadatas", "embeddings"])

    def count(self, collection_name: str = "documents") -> int:
        collection = self.get_or_create_collection(collection_name)
        return collection.count()

    def has_id(self, collection_name: str, doc_id: str) -> bool:
        collection = self.get_or_create_collection(collection_name)
        result = collection.get(ids=[doc_id])
        return len(result["ids"]) > 0

    def get_by_ids(self, collection_name: str, ids: list[str], include: list[str] | None = None) -> dict[str, Any]:
        collection = self.get_or_create_collection(collection_name)
        include = include or ["documents", "metadatas"]
        return collection.get(ids=ids, include=include)

    def delete_by_ids(self, collection_name: str, ids: list[str]) -> None:
        collection = self.get_or_create_collection(collection_name)
        collection.delete(ids=ids)
