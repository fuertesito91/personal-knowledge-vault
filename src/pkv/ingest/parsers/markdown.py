"""Markdown file parser."""

import re
from pathlib import Path
from typing import Any


class MarkdownParser:
    """Parse markdown files, extracting frontmatter and content."""

    def parse(self, file_path: Path) -> dict[str, Any]:
        """Parse a markdown file and return structured data."""
        text = file_path.read_text(encoding="utf-8", errors="replace")
        metadata: dict[str, Any] = {"source_type": "markdown"}

        # Extract YAML frontmatter
        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
        if fm_match:
            import yaml
            try:
                fm = yaml.safe_load(fm_match.group(1)) or {}
                metadata.update(fm)
            except yaml.YAMLError:
                pass
            content = text[fm_match.end():]
        else:
            content = text

        # Extract title from first heading
        title_match = re.match(r"^#\s+(.+)$", content, re.MULTILINE)
        if title_match and "title" not in metadata:
            metadata["title"] = title_match.group(1).strip()
        elif "title" not in metadata:
            metadata["title"] = file_path.stem

        return {"content": content, "metadata": metadata, "title": metadata["title"]}
