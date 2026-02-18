"""Vault maintenance: dedup, fix ontology violations."""

import json
from pathlib import Path
from typing import Any

import yaml


def run_janitor(config: dict[str, Any]) -> dict[str, int]:
    """Run maintenance tasks on the vault.

    Returns stats about what was fixed.
    """
    vault_path = Path(config["vault_path"])
    stats = {"duplicates_removed": 0, "frontmatter_fixed": 0, "orphans_found": 0}

    if not vault_path.exists():
        return stats

    # Check for duplicate content hashes
    hashes: dict[str, list[Path]] = {}
    for md_file in vault_path.rglob("*.md"):
        if md_file.name.startswith("."):
            continue
        text = md_file.read_text(encoding="utf-8", errors="replace")
        # Extract content_hash from frontmatter
        if text.startswith("---"):
            try:
                fm_end = text.index("---", 3)
                fm = yaml.safe_load(text[3:fm_end])
                if fm and "content_hash" in fm:
                    h = fm["content_hash"]
                    hashes.setdefault(h, []).append(md_file)
            except (ValueError, yaml.YAMLError):
                pass

    # Remove duplicates (keep first)
    for h, files in hashes.items():
        if len(files) > 1:
            for dup in files[1:]:
                dup.unlink()
                stats["duplicates_removed"] += 1

    # Validate frontmatter
    for md_file in vault_path.rglob("*.md"):
        if md_file.name.startswith("."):
            continue
        text = md_file.read_text(encoding="utf-8", errors="replace")
        if not text.startswith("---"):
            # Add minimal frontmatter
            fm = {"title": md_file.stem, "type": "Document"}
            new_text = f"---\n{yaml.dump(fm, default_flow_style=False)}---\n{text}"
            md_file.write_text(new_text, encoding="utf-8")
            stats["frontmatter_fixed"] += 1

    return stats
