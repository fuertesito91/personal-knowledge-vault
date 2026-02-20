"""OPTICS clustering of document embeddings."""

import numpy as np
from typing import Any

from ..storage import get_vector_store
from ..models import ClusterResult


def run_clustering(config: dict[str, Any]) -> list[ClusterResult]:
    """Run OPTICS clustering on all document embeddings.

    Returns list of ClusterResult objects.
    """
    from sklearn.cluster import OPTICS

    store = get_vector_store(config)
    data = store.get_all("documents")

    if data["ids"] is None or len(data["ids"]) == 0 or data["embeddings"] is None or len(data["embeddings"]) == 0:
        return []

    embeddings = np.array(data["embeddings"])
    ids = data["ids"]
    metadatas = data["metadatas"] or [{}] * len(ids)

    if len(embeddings) < 3:
        return []

    cluster_cfg = config.get("clustering", {})
    min_samples = cluster_cfg.get("min_samples", 3)
    xi = cluster_cfg.get("xi", 0.05)
    min_cluster_size = cluster_cfg.get("min_cluster_size", 3)

    # Adjust min_samples if we have fewer points
    min_samples = min(min_samples, len(embeddings))

    optics = OPTICS(
        min_samples=min_samples,
        xi=xi,
        min_cluster_size=min_cluster_size,
        metric="cosine",
    )
    labels = optics.fit_predict(embeddings)

    # Group by cluster
    clusters: dict[int, list[int]] = {}
    for idx, label in enumerate(labels):
        if label == -1:  # noise
            continue
        clusters.setdefault(label, []).append(idx)

    results = []
    for cluster_id, member_indices in clusters.items():
        member_embeddings = embeddings[member_indices]
        centroid = member_embeddings.mean(axis=0).tolist()
        doc_ids = [ids[i] for i in member_indices]

        results.append(ClusterResult(
            cluster_id=cluster_id,
            document_ids=doc_ids,
            centroid=centroid,
        ))

    return results
