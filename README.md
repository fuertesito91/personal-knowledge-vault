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

## Individual Commands

```bash
# Run steps individually instead of `pkv pipeline`
pkv ingest              # Process files from inbox
pkv embed               # Embed all unembedded documents
pkv cluster             # Find relationships via OPTICS
pkv enrich              # Claude AI enrichment (optional)
pkv search "query"      # Semantic search
pkv janitor             # Dedup + fix frontmatter
pkv stats               # Show vault statistics
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

## License

MIT
