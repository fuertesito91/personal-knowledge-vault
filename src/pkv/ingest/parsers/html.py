"""HTML file parser."""

from pathlib import Path
from typing import Any


class HtmlParser:
    """Parse HTML files using BeautifulSoup."""

    def parse(self, file_path: Path) -> dict[str, Any]:
        from bs4 import BeautifulSoup

        text = file_path.read_text(encoding="utf-8", errors="replace")
        soup = BeautifulSoup(text, "lxml")

        # Remove scripts and styles
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        title = file_path.stem
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        content = soup.get_text(separator="\n", strip=True)

        return {
            "content": content,
            "metadata": {"source_type": "html"},
            "title": title,
        }
