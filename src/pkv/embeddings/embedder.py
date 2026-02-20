"""Document embedding using sentence-transformers."""

import hashlib
from pathlib import Path
from typing import Any

from rich.progress import Progress

from ..models import ProcessedDocument
from ..storage import get_vector_store


class Embedder:
    """Embeds documents using sentence-transformers and stores in a vector backend."""

    def __init__(self, config: dict[str, Any]):
        self.model_name = config.get("embedding_model", "intfloat/e5-large-v2")
        self.store = get_vector_store(config)
        self._model = None

    @property
    def model(self):
        """Lazy-load the embedding model."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_documents(self, docs: list[ProcessedDocument], collection: str = "documents") -> int:
        """Embed all chunks from documents into ChromaDB.

        Returns number of new chunks embedded.
        """
        ids = []
        texts = []
        metadatas = []

        seen_ids = set()
        for doc in docs:
            for chunk in doc.chunks:
                # Use source path + chunk index + content hash for uniqueness
                chunk_id = hashlib.sha256(
                    f"{doc.source_path}:{doc.content_hash}:{chunk.index}".encode()
                ).hexdigest()[:32]

                # Skip duplicates within this batch
                if chunk_id in seen_ids:
                    continue
                seen_ids.add(chunk_id)

                # Skip already embedded
                if self.store.has_id(collection, chunk_id):
                    continue

                # e5 models need "passage: " prefix for documents
                text = f"passage: {chunk.content}"
                ids.append(chunk_id)
                texts.append(text)
                metadatas.append({
                    "source": doc.source_path,
                    "title": doc.title,
                    "chunk_index": chunk.index,
                    "entity_type": doc.entity_type,
                    "content_hash": doc.content_hash,
                })

        if not ids:
            return 0

        # Embed in batches
        batch_size = 32
        total_embedded = 0

        with Progress() as progress:
            task = progress.add_task("Embedding...", total=len(ids))
            for i in range(0, len(ids), batch_size):
                batch_ids = ids[i:i + batch_size]
                batch_texts = texts[i:i + batch_size]
                batch_meta = metadatas[i:i + batch_size]

                embeddings = self.model.encode(batch_texts).tolist()

                # Store original text (without prefix) in ChromaDB
                original_texts = [t.removeprefix("passage: ") for t in batch_texts]
                self.store.add_documents(
                    collection_name=collection,
                    ids=batch_ids,
                    embeddings=embeddings,
                    documents=original_texts,
                    metadatas=batch_meta,
                )
                total_embedded += len(batch_ids)
                progress.advance(task, len(batch_ids))

        return total_embedded

    def search(self, query: str, collection: str = "documents", n_results: int = 10) -> list[dict]:
        """Semantic search over embedded documents."""
        # e5 models need "query: " prefix for queries
        query_text = f"query: {query}"
        embedding = self.model.encode(query_text).tolist()

        results = self.store.query(collection, embedding, n_results=n_results)

        output = []
        if results and results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                output.append({
                    "id": doc_id,
                    "document": results["documents"][0][i] if results["documents"] else "",
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0,
                })
        return output
