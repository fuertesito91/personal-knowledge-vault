"""PDF file parser."""

import re
from pathlib import Path
from typing import Any


class PdfParser:
    """Parse PDF files using pypdf."""

    def parse(self, file_path: Path) -> dict[str, Any]:
        from pypdf import PdfReader

        reader = PdfReader(str(file_path))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(self._clean_page(text))

        content = "\n\n".join(pages)
        title = file_path.stem

        # Try PDF metadata, but only if it looks like a real title
        meta = reader.metadata
        if meta and meta.title:
            t = meta.title.strip()
            # Skip titles that look like JSON, are too long, or contain control chars
            if not t.startswith(("{", "[")) and len(t) < 200 and "\n" not in t:
                title = t

        return {
            "content": content,
            "metadata": {"source_type": "pdf", "page_count": len(reader.pages)},
            "title": title,
        }

    @staticmethod
    def _clean_page(text: str) -> str:
        """Rejoin words that pypdf splits across lines.

        pypdf often preserves PDF line breaks which results in one-word-per-line
        output for transcripts and flowing text. This joins short lines into
        paragraphs while preserving intentional paragraph breaks (double newlines)
        and lines that look like structure (timestamps, speaker labels, headers).
        """
        lines = text.split("\n")
        paragraphs: list[str] = []
        current: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                # Empty line = paragraph break
                if current:
                    paragraphs.append(" ".join(current))
                    current = []
                continue

            # Check if this line is a structural element (keep on its own line)
            is_structural = bool(
                re.match(r"^\d{2}:\d{2}(:\d{2})?$", stripped)  # timestamp
                or re.match(r"^[A-Z][a-z]+ [A-Z][a-z]+:$", stripped)  # "First Last:"
                or re.match(r"^#{1,6}\s", stripped)  # markdown header
                or re.match(r"^[-*•]\s", stripped)  # list item
            )

            if is_structural:
                if current:
                    paragraphs.append(" ".join(current))
                    current = []
                paragraphs.append(stripped)
            else:
                current.append(stripped)

        if current:
            paragraphs.append(" ".join(current))

        return "\n".join(paragraphs)
