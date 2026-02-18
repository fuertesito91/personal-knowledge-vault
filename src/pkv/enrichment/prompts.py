"""Prompt templates for Claude API enrichment."""

CLUSTER_ANALYSIS_PROMPT = """Analyze these related documents from a personal knowledge base. They were clustered together by semantic similarity.

Documents:
{documents}

Please provide:
1. **Cluster Label**: A short descriptive name for this group of documents (2-5 words)
2. **Shared Entities**: List any people, projects, organizations, or topics mentioned across multiple documents
3. **Relationship Summary**: Describe how these documents relate to each other (1-2 sentences)
4. **Suggested Tags**: 3-5 tags that would help categorize these documents

Respond in this exact JSON format:
{{
  "label": "cluster label here",
  "entities": [
    {{"name": "Entity Name", "type": "Person|Project|Topic|Organization", "mentions": 2}}
  ],
  "relationship_summary": "summary here",
  "tags": ["tag1", "tag2", "tag3"]
}}"""

ENTITY_EXTRACTION_PROMPT = """Extract all named entities from this document. Focus on:
- People (names, roles)
- Projects or products
- Organizations or companies
- Key topics or concepts
- Decisions made

Document:
{document}

Respond in this exact JSON format:
{{
  "entities": [
    {{"name": "Entity Name", "type": "Person|Project|Topic|Organization|Decision", "context": "brief context"}}
  ]
}}"""
