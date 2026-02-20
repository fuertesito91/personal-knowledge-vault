"""Extract and score relationships between documents from clusters."""

import numpy as np
from itertools import combinations
from typing import Any

from ..models import ClusterResult, Relationship
from ..storage import get_vector_store


def extract_relationships(
    clusters: list[ClusterResult],
    config: dict[str, Any],
) -> list[Relationship]:
    """Extract scored relationships from clusters.

    For each cluster, compute pairwise similarity between members.
    """
    store = get_vector_store(config)
    relationships = []

    for cluster in clusters:
        if len(cluster.document_ids) < 2:
            continue

        # Get embeddings for cluster members
        collection = store.get_or_create_collection("documents")
        result = collection.get(ids=cluster.document_ids, include=["embeddings"])

        if result["embeddings"] is None or len(result["embeddings"]) == 0:
            continue

        embeddings = np.array(result["embeddings"])
        ids = result["ids"]

        # Pairwise cosine similarity
        for (i, id_a), (j, id_b) in combinations(enumerate(ids), 2):
            sim = float(np.dot(embeddings[i], embeddings[j]) / (
                np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[j]) + 1e-8
            ))
            relationships.append(Relationship(
                doc_a=id_a,
                doc_b=id_b,
                score=sim,
                cluster_id=cluster.cluster_id,
            ))

    # Sort by score descending
    relationships.sort(key=lambda r: r.score, reverse=True)
    return relationships
