"""Claude API enrichment for clusters and documents."""

import json
from typing import Any

from ..embeddings.store import VectorStore
from ..models import ClusterResult
from ..vault.ontology import OntologyManager
from ..vault.templates import render_entity_page
from .prompts import CLUSTER_ANALYSIS_PROMPT

from pathlib import Path


class Enricher:
    """Enriches knowledge vault using Claude API."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        api_key = config.get("claude_api_key")
        if not api_key:
            raise ValueError("Claude API key required for enrichment. Set ANTHROPIC_API_KEY or claude_api_key in config.")

        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = config.get("claude_model", "claude-opus-4-0725")
        self.store = VectorStore(config["chroma_path"])
        self.ontology = OntologyManager()

    def enrich_clusters(self, clusters: list[ClusterResult]) -> list[dict[str, Any]]:
        """Enrich top clusters with Claude analysis.

        Returns list of enrichment results.
        """
        enrichment_cfg = self.config.get("enrichment", {})
        max_clusters = enrichment_cfg.get("max_clusters", 20)
        max_docs = enrichment_cfg.get("max_docs_per_cluster", 10)

        results = []
        for cluster in clusters[:max_clusters]:
            # Fetch documents for cluster
            collection = self.store.get_or_create_collection("documents")
            doc_ids = cluster.document_ids[:max_docs]
            data = collection.get(ids=doc_ids, include=["documents", "metadatas"])

            if data["documents"] is None or len(data["documents"]) == 0:
                continue

            # Format documents for prompt
            doc_texts = []
            for i, doc in enumerate(data["documents"]):
                meta = data["metadatas"][i] if data["metadatas"] else {}
                title = meta.get("title", f"Document {i+1}")
                doc_texts.append(f"### {title}\n{doc[:1000]}")  # Truncate long docs

            prompt = CLUSTER_ANALYSIS_PROMPT.format(
                documents="\n\n---\n\n".join(doc_texts)
            )

            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1000,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = response.content[0].text
                result = self._parse_json_response(text)
                result["cluster_id"] = cluster.cluster_id
                result["document_ids"] = cluster.document_ids
                results.append(result)

                # Create entity pages for discovered entities
                self._create_entity_pages(result.get("entities", []))

            except Exception as e:
                results.append({
                    "cluster_id": cluster.cluster_id,
                    "error": str(e),
                })

        return results

    @staticmethod
    def _parse_json_response(text: str) -> dict:
        """Extract JSON from Claude's response, handling markdown code blocks."""
        import re
        # Try direct parse first
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try extracting from ```json ... ``` or ``` ... ```
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try finding first { ... } block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        # Give up, return raw text as label
        return {"label": text[:100], "entities": [], "relationship_summary": text, "tags": []}

    def _create_entity_pages(self, entities: list[dict]) -> None:
        """Create vault pages for discovered entities."""
        vault_path = Path(self.config["vault_path"])

        for entity in entities:
            name = entity.get("name", "").strip()
            etype = entity.get("type", "Topic")
            if not name:
                continue

            # Map to ontology type
            if etype not in self.ontology.valid_entity_types():
                etype = "Topic"

            folder = self.ontology.get_entity_folder(etype)
            icon = self.ontology.get_entity_icon(etype)
            target_dir = vault_path / folder
            target_dir.mkdir(parents=True, exist_ok=True)

            # Sanitize name for filesystem (remove / \ : * ? " < > |)
            import re
            safe_name = re.sub(r'[<>:"/\\|?*]', ' - ', name)
            safe_name = re.sub(r'\s+', ' ', safe_name).strip(". ")
            if not safe_name:
                continue

            file_path = target_dir / f"{safe_name}.md"
            if not file_path.exists():
                properties = {
                    "description": entity.get("description", ""),
                    "related_entities": entity.get("related_entities", []),
                    "source_documents": entity.get("source_documents", []),
                    "context": entity.get("context", ""),
                }
                content = render_entity_page(
                    name, etype,
                    properties,
                    icon=icon,
                )
                file_path.write_text(content, encoding="utf-8")
