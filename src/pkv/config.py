"""Configuration management for PKV."""

import os
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG = {
    "vault_path": "~/.pkv/vault",
    "ingest_path": "~/.pkv/ingest",
    "chroma_path": "~/.pkv/chroma",
    "embedding_model": "intfloat/e5-large-v2",
    "claude_model": "claude-sonnet-4-20250514",
    "clustering": {"min_samples": 3, "xi": 0.05, "min_cluster_size": 3},
    "chunking": {"max_tokens": 500, "overlap_tokens": 50, "respect_boundaries": True},
    "enrichment": {"max_clusters": 20, "max_docs_per_cluster": 10},
}


def _find_config_file() -> Path | None:
    """Look for config.yaml in standard locations."""
    candidates = [
        Path.cwd() / "config" / "config.yaml",
        Path.cwd() / "config.yaml",
        Path.home() / ".pkv" / "config.yaml",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load configuration, merging defaults with file and env vars."""
    cfg = dict(DEFAULT_CONFIG)

    path = Path(config_path) if config_path else _find_config_file()
    if path and path.exists():
        with open(path) as f:
            file_cfg = yaml.safe_load(f) or {}
        _deep_merge(cfg, file_cfg)

    # Env overrides
    if api_key := os.environ.get("ANTHROPIC_API_KEY"):
        cfg["claude_api_key"] = api_key

    # Expand paths
    for key in ("vault_path", "ingest_path", "chroma_path"):
        cfg[key] = str(Path(cfg[key]).expanduser().resolve())

    return cfg


def load_ontology(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load ontology definition."""
    candidates = [
        Path.cwd() / "config" / "ontology.yaml",
        Path.home() / ".pkv" / "ontology.yaml",
    ]
    if config_path:
        candidates.insert(0, Path(config_path))

    for p in candidates:
        if p.exists():
            with open(p) as f:
                return yaml.safe_load(f) or {}

    # Return minimal default
    return {"entities": {"Document": {"properties": ["title", "date", "source", "summary"], "folder": "documents"}}, "relationships": []}


def _deep_merge(base: dict, override: dict) -> None:
    """Merge override into base in-place."""
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
