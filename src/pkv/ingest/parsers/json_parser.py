"""JSON parser with special handling for ChatGPT/Claude export formats."""

import json
from pathlib import Path
from typing import Any


class JsonParser:
    """Parse JSON files, with awareness of ChatGPT and Claude export formats."""

    def parse(self, file_path: Path) -> dict[str, Any]:
        text = file_path.read_text(encoding="utf-8", errors="replace")
        data = json.loads(text)
        title = file_path.stem

        # Try ChatGPT export format
        if isinstance(data, list) and data and "mapping" in data[0]:
            return self._parse_chatgpt(data, title)

        # Try ChatGPT single conversation
        if isinstance(data, dict) and "mapping" in data:
            return self._parse_chatgpt([data], title)

        # Try Claude export format (list of conversations with chat_messages)
        if isinstance(data, list) and data and "chat_messages" in data[0]:
            return self._parse_claude(data, title)

        # Generic JSON - stringify
        content = json.dumps(data, indent=2, ensure_ascii=False)
        return {"content": content, "metadata": {"source_type": "json"}, "title": title}

    def _parse_chatgpt(self, conversations: list, title: str) -> dict[str, Any]:
        """Parse ChatGPT export format."""
        parts = []
        for conv in conversations:
            conv_title = conv.get("title", "Untitled")
            parts.append(f"## {conv_title}\n")
            mapping = conv.get("mapping", {})
            # Sort by create_time to maintain order
            messages = []
            for node in mapping.values():
                msg = node.get("message")
                if msg and msg.get("content", {}).get("parts"):
                    role = msg.get("author", {}).get("role", "unknown")
                    content_parts = msg["content"]["parts"]
                    text = "\n".join(str(p) for p in content_parts if isinstance(p, str))
                    if text.strip():
                        create_time = msg.get("create_time") or 0
                        messages.append((create_time, role, text))
            messages.sort(key=lambda x: x[0])
            for _, role, text in messages:
                parts.append(f"**{role}**: {text}\n")

        content = "\n".join(parts)
        return {
            "content": content,
            "metadata": {"source_type": "conversation", "platform": "chatgpt"},
            "title": title if title != file_path_stem else conversations[0].get("title", title),
        }

    def _parse_claude(self, conversations: list, title: str) -> dict[str, Any]:
        """Parse Claude export format."""
        parts = []
        for conv in conversations:
            conv_title = conv.get("name", conv.get("title", "Untitled"))
            parts.append(f"## {conv_title}\n")
            for msg in conv.get("chat_messages", []):
                role = msg.get("sender", "unknown")
                text = msg.get("text", "")
                if not text and "content" in msg:
                    content = msg["content"]
                    if isinstance(content, list):
                        text = "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
                    elif isinstance(content, str):
                        text = content
                if text.strip():
                    parts.append(f"**{role}**: {text}\n")

        content = "\n".join(parts)
        return {
            "content": content,
            "metadata": {"source_type": "conversation", "platform": "claude"},
            "title": conversations[0].get("name", title),
        }
