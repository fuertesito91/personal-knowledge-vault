"""Relationship graph traversal."""

import re
from pathlib import Path
from typing import Any


def find_wikilinks(vault_path: str) -> dict[str, list[str]]:
    """Build a graph of wikilink connections in the vault.

    Returns dict mapping document name -> list of linked document names.
    """
    vault = Path(vault_path)
    graph: dict[str, list[str]] = {}

    for md_file in vault.rglob("*.md"):
        if md_file.name.startswith("."):
            continue
        name = md_file.stem
        text = md_file.read_text(encoding="utf-8", errors="replace")
        links = re.findall(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", text)
        graph[name] = links

    return graph


def find_related(entity_name: str, vault_path: str, depth: int = 1) -> dict[str, Any]:
    """Find documents related to an entity by traversing wikilinks.

    Args:
        entity_name: Name of the entity to start from.
        vault_path: Path to the vault.
        depth: How many hops to traverse.

    Returns:
        Dict with related entities at each depth level.
    """
    graph = find_wikilinks(vault_path)
    visited = set()
    current = {entity_name}
    result: dict[int, list[str]] = {}

    for d in range(depth):
        next_level = set()
        for node in current:
            if node in visited:
                continue
            visited.add(node)
            for linked in graph.get(node, []):
                if linked not in visited:
                    next_level.add(linked)
        result[d + 1] = sorted(next_level)
        current = next_level

    return {
        "entity": entity_name,
        "related": result,
        "total": sum(len(v) for v in result.values()),
    }
