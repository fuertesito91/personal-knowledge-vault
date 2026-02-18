"""Semantic search over the knowledge vault."""

from typing import Any

from ..embeddings.embedder import Embedder


def semantic_search(query: str, config: dict[str, Any], n_results: int = 10) -> list[dict]:
    """Run a semantic search query.

    Args:
        query: Natural language search query.
        config: Application config.
        n_results: Number of results to return.

    Returns:
        List of result dicts with document, metadata, and distance.
    """
    embedder = Embedder(config)
    return embedder.search(query, n_results=n_results)
