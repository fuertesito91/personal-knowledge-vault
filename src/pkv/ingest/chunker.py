"""Smart text chunking that respects semantic boundaries."""

import re


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars per token)."""
    return len(text) // 4


def chunk_text(
    text: str,
    max_tokens: int = 500,
    overlap_tokens: int = 50,
    respect_boundaries: bool = True,
) -> list[str]:
    """Split text into chunks respecting paragraph/section boundaries.

    Args:
        text: The text to chunk.
        max_tokens: Maximum tokens per chunk.
        overlap_tokens: Number of overlap tokens between chunks.
        respect_boundaries: If True, try to split at paragraph/section boundaries.

    Returns:
        List of text chunks.
    """
    if estimate_tokens(text) <= max_tokens:
        return [text.strip()] if text.strip() else []

    max_chars = max_tokens * 4
    overlap_chars = overlap_tokens * 4

    if respect_boundaries:
        # Split into paragraphs first
        blocks = re.split(r"\n\s*\n", text)
    else:
        blocks = [text]

    chunks: list[str] = []
    current = ""

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        if len(current) + len(block) + 2 <= max_chars:
            current = f"{current}\n\n{block}" if current else block
        else:
            if current:
                chunks.append(current.strip())
            # If single block exceeds max, force-split by sentences
            if len(block) > max_chars:
                sentences = re.split(r"(?<=[.!?])\s+", block)
                current = ""
                for sent in sentences:
                    if len(current) + len(sent) + 1 <= max_chars:
                        current = f"{current} {sent}" if current else sent
                    else:
                        if current:
                            chunks.append(current.strip())
                        current = sent
            else:
                current = block

    if current.strip():
        chunks.append(current.strip())

    # Add overlap
    if overlap_chars > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_tail = chunks[i - 1][-overlap_chars:]
            overlapped.append(prev_tail + "\n\n" + chunks[i])
        return overlapped

    return chunks
