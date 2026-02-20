"""ChromaDB wrapper for persistent vector storage.

DEPRECATED: This module is kept for backward compatibility.
New code should use pkv.storage.get_vector_store() instead.
"""

from pathlib import Path
from typing import Any

from ..storage.chromadb import ChromaVectorStore


class VectorStore(ChromaVectorStore):
    """Legacy wrapper — delegates to ChromaVectorStore."""
    pass
