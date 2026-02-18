"""Write processed documents to the Obsidian vault."""

import json
import re
from pathlib import Path
from typing import Any

from ..models import ProcessedDocument
from .ontology import OntologyManager
from .templates import render_document


class VaultWriter:
    """Writes processed documents to an Obsidian-compatible vault."""

    def __init__(self, vault_path: str, ontology: OntologyManager | None = None):
        self.vault_path = Path(vault_path)
        self.ontology = ontology or OntologyManager()
        self._hashes_file = self.vault_path / ".pkv_hashes.json"
        self._hashes = self._load_hashes()

    def _load_hashes(self) -> dict[str, str]:
        """Load known content hashes to avoid duplicates."""
        if self._hashes_file.exists():
            return json.loads(self._hashes_file.read_text())
        return {}

    def _save_hashes(self) -> None:
        self._hashes_file.parent.mkdir(parents=True, exist_ok=True)
        self._hashes_file.write_text(json.dumps(self._hashes, indent=2))

    def write(self, doc: ProcessedDocument) -> Path | None:
        """Write a processed document to the vault.

        Returns the path of the written file, or None if duplicate.
        """
        # Dedup check
        if doc.content_hash in self._hashes:
            return None

        folder = self.ontology.get_entity_folder(doc.entity_type)
        target_dir = self.vault_path / folder
        target_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize filename
        safe_title = self._sanitize_filename(doc.title)
        file_path = target_dir / f"{safe_title}.md"

        # Handle name collisions
        counter = 1
        while file_path.exists():
            file_path = target_dir / f"{safe_title}_{counter}.md"
            counter += 1

        # Extract entities
        entities = self.ontology.extract_entities(doc.content)
        doc.entities = entities

        frontmatter: dict[str, Any] = {
            "title": doc.title,
            "date": doc.date,
            "source": doc.source_path,
            "type": doc.entity_type,
            "source_type": doc.source_type,
            "content_hash": doc.content_hash,
        }
        if doc.tags:
            frontmatter["tags"] = doc.tags
        if entities:
            frontmatter["entities"] = entities

        content = render_document(doc.title, doc.content, frontmatter, entities)
        file_path.write_text(content, encoding="utf-8")

        # Record hash
        self._hashes[doc.content_hash] = str(file_path.relative_to(self.vault_path))
        self._save_hashes()

        return file_path

    def write_many(self, docs: list[ProcessedDocument]) -> list[Path]:
        """Write multiple documents. Returns list of written paths."""
        paths = []
        for doc in docs:
            path = self.write(doc)
            if path:
                paths.append(path)
        return paths

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Sanitize a string for use as a filename."""
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        name = name.strip(". ")
        return name[:100] if name else "untitled"
