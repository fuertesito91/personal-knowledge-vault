"""RAG-based Q&A over the knowledge vault."""

from typing import Any

import anthropic

from .query.search import semantic_search


def ask_question(question: str, config: dict[str, Any], n_chunks: int = 10, since: str | None = None) -> dict:
    """Answer a question using RAG over the vault.

    Returns dict with 'answer' and 'sources' (list of document titles).
    """
    api_key = config.get("claude_api_key")
    if not api_key:
        raise ValueError(
            "Claude API key required. Set ANTHROPIC_API_KEY or claude_api_key in config."
        )

    # Auto-detect date queries and apply since filter
    from datetime import datetime, timedelta
    if not since:
        q_lower = question.lower()
        if any(w in q_lower for w in ["today", "this morning", "this afternoon"]):
            since = "today"
        elif "yesterday" in q_lower:
            since = "yesterday"
        elif any(w in q_lower for w in ["this week", "past week", "last few days"]):
            since = "week"

    # Resolve since to a date string
    since_date = None
    if since:
        if since == "today":
            since_date = datetime.now().strftime("%Y-%m-%d")
        elif since == "yesterday":
            since_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        elif since == "week":
            since_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        else:
            since_date = since

    # For date queries: scan vault filenames for matching dates, read directly
    if since_date:
        import re
        from pathlib import Path

        vault_path = Path(config["vault_path"])
        date_results = []

        # Scan all vault files for date patterns in filenames
        for f in sorted(vault_path.rglob("*.md")):
            # Extract date from filename (YYYY/MM/DD, YYYY_MM_DD, YYYYMMDD)
            m = re.search(r'(\d{4})[/_](\d{2})[/_](\d{2})', f.name)
            if not m:
                m = re.search(r'(\d{4})(\d{2})(\d{2})', f.name)
            if not m:
                continue

            file_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            if file_date >= since_date:
                # Read first ~2000 chars for context (enough for summary)
                content = f.read_text(errors="replace")[:2000]
                title = f.stem
                date_results.append({
                    "id": str(f),
                    "document": content,
                    "metadata": {"title": title, "document_date": file_date, "source": str(f)},
                    "distance": 0,
                })

        # Also include semantic search results for the question
        semantic_results = semantic_search(question, config, n_results=n_chunks)
        seen_titles = {r["metadata"].get("title", "") for r in date_results}
        for r in semantic_results:
            if r["metadata"].get("title", "") not in seen_titles:
                date_results.append(r)

        results = date_results
    else:
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

    from datetime import datetime
    today = datetime.now().strftime("%A, %Y-%m-%d")

    response = client.messages.create(
        model=model,
        max_tokens=2000,
        system=f"You are a helpful assistant answering questions based on the user's personal knowledge base. "
               f"Today is {today}. "
               f"Use ONLY the provided context to answer. If the context doesn't contain enough information, say so. "
               f"Reference specific documents by their titles when relevant. "
               f"Document titles often contain dates in formats like 'YYYY/MM/DD' or 'YYYYMMDD'. Use these to answer date-related questions. "
               f"Be direct and concise — answer the question, don't hedge unnecessarily.",
        messages=[{
            "role": "user",
            "content": f"Context from my knowledge vault:\n\n{context}\n\n---\n\nQuestion: {question}",
        }],
    )

    return {
        "answer": response.content[0].text,
        "sources": list(sources.keys()),
    }
