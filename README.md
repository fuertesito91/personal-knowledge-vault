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

## Installation

```bash
# Clone
git clone https://github.com/fuertesito91/personal-knowledge-vault.git
cd personal-knowledge-vault

# Install in development mode
pip install -e .

# Or install from PyPI (when published)
# pip install personal-knowledge-vault
```

## Quick Start

```bash
# 1. Initialize vault
pkv init

# 2. Drop files into ~/.pkv/ingest/
cp my-notes.md ~/.pkv/ingest/
cp chatgpt-export.json ~/.pkv/ingest/
cp research-paper.pdf ~/.pkv/ingest/

# 3. Run ingestion
pkv ingest

# 4. Embed documents
pkv embed

# 5. Search
pkv search "machine learning applications"

# 6. Run clustering
pkv cluster

# 7. (Optional) Enrich with Claude
export ANTHROPIC_API_KEY=sk-ant-...
pkv enrich

# Or run everything at once:
pkv pipeline
```

## CLI Reference

| Command | Description |
|---------|-------------|
| `pkv init [--path PATH]` | Initialize vault + config |
| `pkv ingest [PATH]` | Process files from ingest dir or specific path |
| `pkv embed` | Embed all unembedded documents |
| `pkv search "query" [-n N]` | Semantic search (default 5 results) |
| `pkv cluster` | Run OPTICS clustering |
| `pkv enrich` | Claude AI enrichment on clusters |
| `pkv janitor` | Dedup + fix frontmatter |
| `pkv stats` | Show vault statistics |
| `pkv pipeline` | Full pipeline: ingest → embed → cluster → enrich |

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
