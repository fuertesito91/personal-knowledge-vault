# Architecture

## Pipeline

```
File Drop → Parser → Chunker → Vault Writer → Embedder → ChromaDB → OPTICS → Claude Enrichment
```

### 1. Ingestion (`pkv.ingest`)
Files are detected by extension, parsed into text + metadata, chunked respecting semantic boundaries (paragraphs, sections), and wrapped in `ProcessedDocument` objects.

### 2. Vault (`pkv.vault`)
Documents are written as Obsidian-compatible markdown with YAML frontmatter. Entity extraction creates `[[wikilinks]]`. Content hashing prevents duplicates.

### 3. Embeddings (`pkv.embeddings`)
Uses `intfloat/e5-large-v2` via sentence-transformers. Chunks are embedded with "passage:" prefix (e5 convention). Stored in ChromaDB with metadata. Incremental — skips already-embedded chunks.

### 4. Clustering (`pkv.clustering`)
OPTICS algorithm finds density-based clusters in embedding space. Pairwise cosine similarity scores relationships within clusters.

### 5. Enrichment (`pkv.enrichment`)
Claude API analyzes top clusters: labels them, extracts shared entities, suggests relationships. Creates entity pages in the vault automatically.

### 6. Query (`pkv.query`)
Semantic search uses "query:" prefix for e5 model. Graph traversal follows wikilinks to find related entities.
