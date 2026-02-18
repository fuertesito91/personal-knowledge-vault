"""RAG-based Q&A over the knowledge vault."""

from typing import Any

import anthropic

from .query.search import semantic_search


def ask_question(question: str, config: dict[str, Any], n_chunks: int = 10) -> dict:
    """Answer a question using RAG over the vault.

    Returns dict with 'answer' and 'sources' (list of document titles).
    """
    api_key = config.get("claude_api_key")
    if not api_key:
        raise ValueError(
            "Claude API key required. Set ANTHROPIC_API_KEY or claude_api_key in config."
        )

    results = semantic_search(question, config, n_results=n_chunks)
    if not results:
        return {"answer": "No relevant documents found. Have you run 'pkv embed'?", "sources": []}

    # Build context from search results
    context_parts = []
    sources = {}
    for i, r in enumerate(results, 1):
        title = r["metadata"].get("title", "Unknown")
        sources[title] = True
        context_parts.append(f"[{i}] {title}:\n{r['document']}")

    context = "\n\n---\n\n".join(context_parts)

    client = anthropic.Anthropic(api_key=api_key)
    model = config.get("claude_model", "claude-opus-4-0725")

    response = client.messages.create(
        model=model,
        max_tokens=2000,
        system="You are a helpful assistant answering questions based on the user's personal knowledge base. "
               "Use ONLY the provided context to answer. If the context doesn't contain enough information, say so. "
               "Reference specific documents by their titles when relevant.",
        messages=[{
            "role": "user",
            "content": f"Context from my knowledge vault:\n\n{context}\n\n---\n\nQuestion: {question}",
        }],
    )

    return {
        "answer": response.content[0].text,
        "sources": list(sources.keys()),
    }
