"""PDF file parser."""

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
                pages.append(text)

        content = "\n\n".join(pages)
        title = file_path.stem

        # Try PDF metadata
        meta = reader.metadata
        if meta and meta.title:
            title = meta.title

        return {
            "content": content,
            "metadata": {"source_type": "pdf", "page_count": len(reader.pages)},
            "title": title,
        }
