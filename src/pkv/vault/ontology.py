"""Ontology management and entity extraction."""

import re
from typing import Any

from ..config import load_ontology


class OntologyManager:
    """Manages entity types and relationships from ontology config."""

    def __init__(self, ontology: dict[str, Any] | None = None):
        self.ontology = ontology or load_ontology()
        self.entities = self.ontology.get("entities", {})
        self.relationships = self.ontology.get("relationships", [])

    def get_entity_folder(self, entity_type: str) -> str:
        """Get the vault folder for an entity type."""
        entity = self.entities.get(entity_type, {})
        return entity.get("folder", "documents")

    def get_entity_properties(self, entity_type: str) -> list[str]:
        """Get properties for an entity type."""
        entity = self.entities.get(entity_type, {})
        return entity.get("properties", [])

    def get_entity_icon(self, entity_type: str) -> str:
        """Get icon for an entity type."""
        entity = self.entities.get(entity_type, {})
        return entity.get("icon", "📄")

    def extract_entities(self, text: str) -> list[str]:
        """Extract potential entity names from text using simple heuristics.

        Looks for:
        - Capitalized multi-word phrases (potential names)
        - Existing wikilinks [[entity]]
        """
        entities = set()

        # Existing wikilinks
        for match in re.finditer(r"\[\[([^\]]+)\]\]", text):
            entities.add(match.group(1))

        # Capitalized phrases (2-4 words, likely proper nouns)
        for match in re.finditer(r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+){1,3})\b", text):
            name = match.group(1)
            # Filter out common false positives
            if name not in {"The", "This", "That", "These", "Those", "Monday", "Tuesday",
                           "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
                           "January", "February", "March", "April", "May", "June",
                           "July", "August", "September", "October", "November", "December"}:
                entities.add(name)

        return sorted(entities)

    def valid_entity_types(self) -> list[str]:
        """Return list of valid entity type names."""
        return list(self.entities.keys())
