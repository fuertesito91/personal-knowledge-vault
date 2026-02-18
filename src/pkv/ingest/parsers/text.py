"""Plain text file parser."""

from pathlib import Path
from typing import Any


class TextParser:
    """Parse plain text files."""

    def parse(self, file_path: Path) -> dict[str, Any]:
        text = file_path.read_text(encoding="utf-8", errors="replace")
        title = file_path.stem
        # Try first line as title if short enough
        first_line = text.split("\n", 1)[0].strip()
        if first_line and len(first_line) < 120:
            title = first_line

        return {
            "content": text,
            "metadata": {"source_type": "text"},
            "title": title,
        }
