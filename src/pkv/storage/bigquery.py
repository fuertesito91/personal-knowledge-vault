"""BigQuery vector store backend.

Uses brute-force cosine similarity for <10K chunks (no VECTOR_INDEX needed).
All GCP imports are lazy — this module is only loaded when storage_backend=bigquery.
"""

import json
import time
from datetime import datetime, timezone
from typing import Any


def _get_bq_client(project: str):
    from google.cloud import bigquery
    return bigquery.Client(project=project)


class BigQueryVectorStore:
    """BigQuery-backed vector store with cosine similarity search."""

    def __init__(self, project: str, dataset: str, table: str):
        self.project = project
        self.dataset = dataset
        self.table = table
        self.full_table = f"{project}.{dataset}.{table}"
        self._client = None
        self._ensure_table()

    @property
    def client(self):
        if self._client is None:
            self._client = _get_bq_client(self.project)
        return self._client

    def _ensure_table(self):
        """Create table if it doesn't exist."""
        from google.cloud import bigquery

        schema = [
            bigquery.SchemaField("chunk_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("content", "STRING"),
            bigquery.SchemaField("title", "STRING"),
            bigquery.SchemaField("source", "STRING"),
            bigquery.SchemaField("metadata", "STRING"),  # JSON as string
            bigquery.SchemaField("embedding", "FLOAT64", mode="REPEATED"),
            bigquery.SchemaField("created_at", "TIMESTAMP"),
        ]

        table_ref = bigquery.Table(self.full_table, schema=schema)
        try:
            self.client.get_table(self.full_table)
        except Exception:
            self.client.create_table(table_ref)

    def get_or_create_collection(self, name: str = "documents") -> "BigQueryCollection":
        """Return a collection-like wrapper (for compatibility with code that calls collection.get())."""
        return BigQueryCollection(self, name)

    def add_documents(
        self,
        collection_name: str,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """Upsert documents with embeddings to BigQuery."""
        if not ids:
            return

        metadatas = metadatas or [{}] * len(ids)
        now = datetime.now(timezone.utc).isoformat()

        # Delete existing rows with these IDs first (upsert)
        self.delete_by_ids(collection_name, ids)

        rows = []
        for i, chunk_id in enumerate(ids):
            meta = metadatas[i] if i < len(metadatas) else {}
            rows.append({
                "chunk_id": chunk_id,
                "content": documents[i] if i < len(documents) else "",
                "title": meta.get("title", ""),
                "source": meta.get("source", ""),
                "metadata": json.dumps(meta),
                "embedding": embeddings[i],
                "created_at": now,
            })

        # Insert in batches of 500
        for batch_start in range(0, len(rows), 500):
            batch = rows[batch_start:batch_start + 500]
            errors = self.client.insert_rows_json(self.full_table, batch)
            if errors:
                raise RuntimeError(f"BigQuery insert errors: {errors}")

    def query(
        self,
        collection_name: str,
        query_embedding: list[float],
        n_results: int = 10,
    ) -> dict[str, Any]:
        """Cosine similarity search."""
        # Build the embedding array literal
        emb_str = ", ".join(str(v) for v in query_embedding)

        sql = f"""
        WITH query AS (
            SELECT [{emb_str}] AS qemb
        )
        SELECT
            t.chunk_id,
            t.content,
            t.metadata,
            -- cosine distance (1 - cosine_similarity) to match ChromaDB convention
            1.0 - (
                (SELECT SUM(a * b) FROM UNNEST(t.embedding) a WITH OFFSET i
                 JOIN UNNEST(q.qemb) b WITH OFFSET j ON i = j)
                / NULLIF(
                    SQRT((SELECT SUM(a * a) FROM UNNEST(t.embedding) a))
                    * SQRT((SELECT SUM(b * b) FROM UNNEST(q.qemb) b)),
                    0)
            ) AS distance
        FROM `{self.full_table}` t, query q
        WHERE ARRAY_LENGTH(t.embedding) > 0
        ORDER BY distance ASC
        LIMIT {n_results}
        """

        result = self.client.query(sql).result()
        ids = []
        documents = []
        metadatas = []
        distances = []

        for row in result:
            ids.append(row.chunk_id)
            documents.append(row.content or "")
            try:
                metadatas.append(json.loads(row.metadata) if row.metadata else {})
            except (json.JSONDecodeError, TypeError):
                metadatas.append({})
            distances.append(float(row.distance) if row.distance is not None else 1.0)

        return {
            "ids": [ids],
            "documents": [documents],
            "metadatas": [metadatas],
            "distances": [distances],
        }

    def get_all(self, collection_name: str = "documents") -> dict[str, Any]:
        """Get all documents and embeddings."""
        sql = f"SELECT chunk_id, content, metadata, embedding FROM `{self.full_table}`"
        result = self.client.query(sql).result()

        ids = []
        documents = []
        metadatas = []
        embeddings = []

        for row in result:
            ids.append(row.chunk_id)
            documents.append(row.content or "")
            try:
                metadatas.append(json.loads(row.metadata) if row.metadata else {})
            except (json.JSONDecodeError, TypeError):
                metadatas.append({})
            embeddings.append(list(row.embedding) if row.embedding else [])

        return {"ids": ids, "documents": documents, "metadatas": metadatas, "embeddings": embeddings}

    def count(self, collection_name: str = "documents") -> int:
        sql = f"SELECT COUNT(*) as cnt FROM `{self.full_table}`"
        result = self.client.query(sql).result()
        for row in result:
            return row.cnt
        return 0

    def has_id(self, collection_name: str, doc_id: str) -> bool:
        sql = f"SELECT 1 FROM `{self.full_table}` WHERE chunk_id = @id LIMIT 1"
        from google.cloud.bigquery import ScalarQueryParameter, QueryJobConfig
        job_config = QueryJobConfig(query_parameters=[
            ScalarQueryParameter("id", "STRING", doc_id),
        ])
        result = self.client.query(sql, job_config=job_config).result()
        return sum(1 for _ in result) > 0

    def get_by_ids(self, collection_name: str, ids: list[str], include: list[str] | None = None) -> dict[str, Any]:
        """Get documents by IDs."""
        if not ids:
            return {"ids": [], "documents": [], "metadatas": [], "embeddings": []}

        include = include or ["documents", "metadatas"]
        cols = ["chunk_id"]
        if "documents" in include:
            cols.append("content")
        if "metadatas" in include:
            cols.append("metadata")
        if "embeddings" in include:
            cols.append("embedding")

        placeholders = ", ".join(f"'{id_}'" for id_ in ids)
        sql = f"SELECT {', '.join(cols)} FROM `{self.full_table}` WHERE chunk_id IN ({placeholders})"
        result = self.client.query(sql).result()

        out: dict[str, list] = {"ids": [], "documents": [], "metadatas": [], "embeddings": []}
        for row in result:
            out["ids"].append(row.chunk_id)
            if "documents" in include:
                out["documents"].append(row.content or "")
            if "metadatas" in include:
                try:
                    out["metadatas"].append(json.loads(row.metadata) if row.metadata else {})
                except (json.JSONDecodeError, TypeError):
                    out["metadatas"].append({})
            if "embeddings" in include:
                out["embeddings"].append(list(row.embedding) if row.embedding else [])

        return out

    def delete_by_ids(self, collection_name: str, ids: list[str]) -> None:
        if not ids:
            return
        placeholders = ", ".join(f"'{id_}'" for id_ in ids)
        sql = f"DELETE FROM `{self.full_table}` WHERE chunk_id IN ({placeholders})"
        self.client.query(sql).result()


class BigQueryCollection:
    """Thin wrapper so code like `collection.get(ids=..., include=...)` works."""

    def __init__(self, store: BigQueryVectorStore, name: str):
        self._store = store
        self._name = name

    def get(self, ids: list[str] | None = None, include: list[str] | None = None) -> dict[str, Any]:
        if ids:
            return self._store.get_by_ids(self._name, ids, include)
        return self._store.get_all(self._name)

    def count(self) -> int:
        return self._store.count(self._name)
