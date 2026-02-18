# Query Guide

## Semantic Search

```bash
pkv search "what decisions were made about the API design?"
pkv search "meetings with John" -n 10
```

Results show title, similarity score, and a text preview.

## Graph Traversal

The vault uses `[[wikilinks]]` for relationships. Open the vault in Obsidian to visually explore the graph, or use the Python API:

```python
from pkv.query.graph import find_related
result = find_related("John Smith", "~/.pkv/vault", depth=2)
```

## From Claude / OpenClaw

You can query the vault programmatically:

```python
from pkv.config import load_config
from pkv.query.search import semantic_search

config = load_config()
results = semantic_search("project status updates", config)
for r in results:
    print(r["metadata"]["title"], r["distance"])
```
