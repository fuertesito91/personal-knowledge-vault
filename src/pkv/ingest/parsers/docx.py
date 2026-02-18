"""DOCX file parser."""

from pathlib import Path
from typing import Any


class DocxParser:
    """Parse DOCX files using python-docx."""

    def parse(self, file_path: Path) -> dict[str, Any]:
        from docx import Document

        doc = Document(str(file_path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        content = "\n\n".join(paragraphs)

        title = file_path.stem
        if doc.core_properties.title:
            title = doc.core_properties.title

        return {
            "content": content,
            "metadata": {"source_type": "docx"},
            "title": title,
        }
