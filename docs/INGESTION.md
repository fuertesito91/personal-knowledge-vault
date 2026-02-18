# Ingestion Guide

## How It Works

1. Drop any supported file into the ingest directory (`~/.pkv/ingest/`)
2. Run `pkv ingest`
3. Files are parsed, chunked, and written to the vault as markdown

## Supported Formats

- **Markdown** (`.md`): Preserves existing frontmatter
- **Text** (`.txt`, `.log`, `.csv`): Uses first line as title
- **JSON** (`.json`): Auto-detects ChatGPT/Claude export formats
- **HTML** (`.html`): Strips scripts/nav, extracts readable text
- **PDF** (`.pdf`): Extracts text from all pages
- **DOCX** (`.docx`): Extracts paragraphs

## Deduplication

Every document is hashed (SHA256). Re-ingesting the same content is a no-op.

## Chunking

Text is split into ~500 token chunks respecting paragraph boundaries, with 50-token overlap for context continuity.
