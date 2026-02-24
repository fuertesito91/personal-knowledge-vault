"""Document embedding using sentence-transformers."""

import hashlib
import re
from pathlib import Path
from typing import Any


def _extract_date_from_title(title: str) -> str | None:
    """Extract ISO date from title like 'Meeting – 2026/02/16 11:00 GMT – Notes by Gemini'.

    Also handles underscored format: '2026_02_24 10_00 GMT'.
    Returns 'YYYY-MM-DD' or None.
    """
    # Match YYYY/MM/DD or YYYY_MM_DD
    m = re.search(r'(\d{4})[/_](\d{2})[/_](\d{2})', title)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    # Match YYYYMMDD
    m = re.search(r'(\d{4})(\d{2})(\d{2})', title)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 2000 <= y <= 2099 and 1 <= mo <= 12 and 1 <= d <= 31:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None

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
                meta = {
                    "source": doc.source_path,
                    "title": doc.title,
                    "chunk_index": chunk.index,
                    "entity_type": doc.entity_type,
                    "content_hash": doc.content_hash,
                }
                # Extract date from title (e.g. "Meeting – 2026/02/16 11:00 GMT – Notes by Gemini")
                doc_date = _extract_date_from_title(doc.title)
                if doc_date:
                    meta["document_date"] = doc_date
                metadatas.append(meta)

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
