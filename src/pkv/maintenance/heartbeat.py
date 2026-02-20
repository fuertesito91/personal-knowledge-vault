"""Heartbeat: summarize recent activity and load relevant context."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


def get_recent_documents(config: dict[str, Any], days: int = 7) -> list[dict[str, Any]]:
    """Get documents modified in the last N days."""
    vault_path = Path(config["vault_path"])
    if not vault_path.exists():
        return []

    cutoff = datetime.now() - timedelta(days=days)
    recent = []

    for md_file in vault_path.rglob("*.md"):
        if md_file.name.startswith("."):
            continue
        mtime = datetime.fromtimestamp(md_file.stat().st_mtime)
        if mtime >= cutoff:
            recent.append({
                "path": str(md_file),
                "name": md_file.stem,
                "modified": mtime.isoformat(),
            })

    recent.sort(key=lambda x: x["modified"], reverse=True)
    return recent


def vault_stats(config: dict[str, Any]) -> dict[str, Any]:
    """Get vault statistics."""
    vault_path = Path(config["vault_path"])
    if not vault_path.exists():
        return {"total_documents": 0, "folders": {}}

    stats: dict[str, Any] = {"total_documents": 0, "folders": {}}
    for md_file in vault_path.rglob("*.md"):
        if md_file.name.startswith("."):
            continue
        stats["total_documents"] += 1
        folder = md_file.parent.relative_to(vault_path).parts
        folder_name = folder[0] if folder else "root"
        stats["folders"][folder_name] = stats["folders"].get(folder_name, 0) + 1

    # ChromaDB stats
    try:
        from ..storage import get_vector_store
        store = get_vector_store(config)
        stats["embedded_chunks"] = store.count("documents")
    except Exception:
        stats["embedded_chunks"] = 0

    return stats
