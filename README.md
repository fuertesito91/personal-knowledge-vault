# Personal Knowledge Vault (PKV)

A personal knowledge base system that ingests any document, organizes it into an Obsidian-compatible vault, vectorizes everything, clusters to find hidden relationships, and optionally enriches with Claude AI.

```
Ingest (drop anything)  →  Process/Chunk  →  Obsidian Vault (markdown + frontmatter)
                                                       ↓
                                             Embed (e5-large via sentence-transformers)
                                                       ↓
                                             ChromaDB (local vector store)
                                                       ↓
                                             OPTICS Clustering (sklearn)
                                                       ↓
                                             Claude API Enrichment (optional)
                                                       ↓
                                             Query CLI / Semantic Search
```

## Features

- **Source-agnostic ingestion**: Drop markdown, text, PDF, DOCX, HTML, JSON (including ChatGPT/Claude exports) — it all gets processed
- **Obsidian-native**: Everything stored as markdown with YAML frontmatter and `[[wikilinks]]`
- **Ontology system**: Configurable entity types (Person, Project, Meeting, etc.) with typed relationships
- **Semantic search**: Vector-based search using e5-large embeddings + ChromaDB
- **Automatic clustering**: OPTICS finds hidden connections between documents
- **AI enrichment**: Claude labels clusters, extracts entities, creates relationship pages
- **Idempotent**: Re-running on same files won't create duplicates (SHA256 content hashing)
- **Local-first**: All data on disk. Claude API is optional, only for enrichment.

## Requirements

- Python 3.10+
- [Obsidian](https://obsidian.md/) (optional, for viewing the vault)

## Installation & Setup

### Step 1: Clone and install

```bash
git clone https://github.com/fuertesito91/personal-knowledge-vault.git
cd personal-knowledge-vault

# Create a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate

# Install
pip install -e .
```

### Step 2: Initialize your vault

```bash
pkv init
```

This creates everything under `~/.pkv/`:
- `vault/` — your Obsidian vault (markdown files live here)
- `ingest/` — your inbox (drop files here to process them)
- `chroma/` — vector store (semantic search index)
- `config.yaml` — configuration

### Step 3: Set up Claude enrichment (optional)

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Or add `claude_api_key: sk-ant-...` to `~/.pkv/config.yaml`.

### Step 4: Open the vault in Obsidian

1. Download & install [Obsidian](https://obsidian.md/)
2. Open Obsidian → **"Open folder as vault"**
3. Point it to `~/.pkv/vault`
4. Keep it open — it updates live as you ingest content

### Step 5: Drop your files and run

```bash
# Drop any files into the inbox
cp ~/meeting-notes.md ~/.pkv/ingest/
cp ~/chatgpt-export.json ~/.pkv/ingest/
cp ~/report.pdf ~/.pkv/ingest/

# Run the full pipeline (ingest → embed → cluster → enrich)
pkv pipeline
```

First run downloads the e5-large embedding model (~1.3GB) — after that it's cached.

### Step 6: Browse in Obsidian

Your documents are now organized into folders (`documents/`, `conversations/`, `meetings/`, etc.) with YAML frontmatter, `[[wikilinks]]` between entities, and auto-generated entity pages.

### Day-to-day usage

1. **Drop files** into `~/.pkv/ingest/`
2. **Run** `pkv pipeline`
3. **Search** with `pkv search "whatever you're looking for"`
4. **Browse** in Obsidian

It's idempotent — re-running on the same files won't create duplicates.

## Pipeline Steps Explained

You can run the full pipeline with `pkv pipeline`, or run each step individually:

### `pkv init`

Creates the PKV directory structure at `~/.pkv/`. This is your one-time setup:

- `vault/` — Obsidian-compatible markdown vault (your knowledge base lives here)
- `ingest/` — inbox folder where you drop files to process
- `chroma/` — ChromaDB vector store for semantic search
- `config.yaml` — settings (model, paths, clustering params, API keys)
- `ontology.yaml` — entity types and relationship definitions

Safe to re-run — won't overwrite existing files.

### `pkv ingest`

Processes files from your inbox (`~/.pkv/ingest/`) into the vault:

1. **Reads** each file (markdown, PDF, DOCX, HTML, JSON, plain text)
2. **Detects type** — meeting transcripts go to `meetings/`, chat exports to `conversations/`, everything else to `documents/`
3. **Extracts metadata** — title, date, source path, content hash
4. **Chunks** large documents into ~500-token pieces with overlap
5. **Writes** markdown files with YAML frontmatter into the vault

Idempotent — same file won't be ingested twice (SHA256 content hashing).

### `pkv embed`

Vectorizes all documents using the [e5-large-v2](https://huggingface.co/intfloat/e5-large-v2) embedding model:

1. **Scans** the vault for unembedded documents
2. **Generates** 1024-dimensional embeddings for each chunk
3. **Stores** vectors in ChromaDB (local, no external API)

First run downloads the model (~1.3GB). Subsequent runs only embed new/changed documents.

### `pkv cluster`

Finds hidden relationships between documents using [OPTICS](https://en.wikipedia.org/wiki/OPTICS_algorithm) clustering:

1. **Retrieves** all embeddings from ChromaDB
2. **Runs** OPTICS density-based clustering (finds natural groupings without needing a fixed cluster count)
3. **Labels** each cluster and writes cluster metadata to the vault

Documents that cover similar topics end up in the same cluster, even if they were ingested from completely different sources.

### `pkv enrich`

**Optional** — requires a Claude API key. Uses AI to enhance your vault:

1. **Reads** each cluster's documents
2. **Extracts entities** — people, projects, topics, decisions mentioned across documents
3. **Creates entity pages** with `[[wikilinks]]` connecting them to source documents
4. **Labels clusters** with human-readable summaries
5. **Maps relationships** between entities (e.g., Person → works_on → Project)

This is the step that turns a pile of documents into a connected knowledge graph you can browse in Obsidian.

### Other Commands

```bash
pkv search "query"      # Semantic search across all documents
pkv pipeline            # Run ingest → embed → cluster → enrich in one go
pkv janitor             # Dedup chunks + fix frontmatter issues
pkv stats               # Show vault statistics (doc count, embeddings, clusters)
```

## Configuration

Default location: `~/.pkv/config.yaml`

```yaml
vault_path: ~/.pkv/vault          # Obsidian vault location
ingest_path: ~/.pkv/ingest        # Drop files here
chroma_path: ~/.pkv/chroma        # Vector store location
embedding_model: intfloat/e5-large-v2  # Sentence-transformers model

# Optional: Claude API for enrichment
# claude_api_key: sk-ant-...      # Or set ANTHROPIC_API_KEY env var
claude_model: claude-sonnet-4-20250514

clustering:
  min_samples: 3
  xi: 0.05
  min_cluster_size: 3

chunking:
  max_tokens: 500
  overlap_tokens: 50
  respect_boundaries: true

enrichment:
  max_clusters: 20
  max_docs_per_cluster: 10
```

## Ontology

PKV uses a configurable ontology to type documents and entities. Edit `ontology.yaml`:

```yaml
entities:
  Person:
    properties: [name, role, organization, notes]
    folder: entities/people
    icon: 👤
  Project:
    properties: [name, status, description, stakeholders]
    folder: entities/projects
    icon: 📋
  Meeting:
    properties: [date, participants, summary, decisions, action_items]
    folder: meetings
    icon: 🤝
  Conversation:
    properties: [date, platform, participants, summary, topics]
    folder: conversations
    icon: 💬
  Topic:
    properties: [name, description, related_topics]
    folder: entities/topics
    icon: 🏷️
  Decision:
    properties: [date, context, decision, rationale, stakeholders]
    folder: decisions
    icon: ⚖️
  Document:
    properties: [title, date, source, summary]
    folder: documents
    icon: 📄

relationships:
  - {from: Person, to: Project, type: works_on}
  - {from: Person, to: Meeting, type: attended}
  - {from: Meeting, to: Decision, type: produced}
  - {from: Document, to: Topic, type: covers}
```

## Supported File Formats

| Format | Extension | Notes |
|--------|-----------|-------|
| Markdown | `.md` | Preserves frontmatter |
| Plain text | `.txt`, `.log`, `.csv` | First line as title |
| JSON | `.json` | ChatGPT & Claude export support |
| HTML | `.html`, `.htm` | Strips scripts/nav |
| PDF | `.pdf` | Via pypdf |
| DOCX | `.docx` | Via python-docx |

### ChatGPT/Claude JSON Exports

PKV automatically detects and parses:
- **ChatGPT**: `conversations[].mapping[].message.content` format
- **Claude**: `chat_messages[]` format
- **Generic JSON**: Stringified and chunked

## Vault Structure

```
~/.pkv/vault/
├── documents/          # General documents
├── conversations/      # Chat exports
├── meetings/          # Meeting notes
├── decisions/         # Decision records
└── entities/
    ├── people/        # Person pages
    ├── projects/      # Project pages
    └── topics/        # Topic pages
```

Each document has YAML frontmatter:
```yaml
---
title: My Document
date: 2026-02-17
source: /path/to/original.md
type: Document
source_type: markdown
content_hash: abc123...
tags: [research, AI]
entities: [John Smith, Project Alpha]
---
```

## Using with Obsidian

1. Open Obsidian
2. Select "Open folder as vault"
3. Point to `~/.pkv/vault`
4. All documents, wikilinks, and entity pages are ready to browse

## Coming Soon

- 📁 File watcher (auto-ingest on file drop)
- 🔌 OpenClaw skill for natural language queries
- ⏰ Heartbeat cron (periodic context refresh)
- 🌐 Web UI
- 📧 More parsers (email .eml, .epub, audio transcripts)

## GCP Backends (Optional)

PKV supports optional cloud backends for access from anywhere. Install GCP dependencies:

```bash
pip install -e ".[gcp]"
```

### BigQuery Vector Store

Use BigQuery instead of ChromaDB for vector storage:

1. **Authenticate:**
   ```bash
   gcloud auth application-default login
   ```

2. **Update `config.yaml`:**
   ```yaml
   storage_backend: bigquery
   bigquery:
     project: ozpr-reporting-dev
     dataset: dbt_oriol
     table: pkv_oriol
   ```

3. The table is created automatically on first use. All existing commands (`pkv embed`, `pkv search`, `pkv ask`, etc.) work transparently with BigQuery.

**Notes:**
- Uses brute-force cosine similarity — fast enough for <10K chunks
- For larger scales, consider adding a `VECTOR_INDEX` manually
- Application Default Credentials are used (no service account files needed)

### Google Drive Vault Sync

One-way sync: local vault → Google Drive.

1. **Authenticate** (same as above, needs Drive scope):
   ```bash
   gcloud auth application-default login --scopes="https://www.googleapis.com/auth/drive.file,https://www.googleapis.com/auth/cloud-platform"
   ```

2. **Create a folder in Google Drive** for your vault, copy its folder ID from the URL.

3. **Update `config.yaml`:**
   ```yaml
   vault_sync: gdrive
   gdrive:
     vault_folder_id: "your-drive-folder-id"
   ```

4. **Sync manually or automatically:**
   ```bash
   pkv sync           # manual sync
   pkv pipeline       # sync runs after enrich
   pkv watch          # sync runs after each batch
   ```

Drive sync tracks content hashes to avoid re-uploading unchanged files. Subfolder structure (documents/, meetings/, entities/, etc.) is mirrored in Drive.

## License

MIT
