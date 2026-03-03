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

    # For date queries: get ALL chunks matching the date range first,
    # then supplement with semantic search results
    if since_date:
        from .storage import get_vector_store
        store = get_vector_store(config)
        all_data = store.get_all("documents")
        
        # Filter chunks by document_date metadata
        date_results = []
        seen_ids = set()
        if all_data and all_data.get("ids"):
            for i, doc_id in enumerate(all_data["ids"]):
                meta = all_data["metadatas"][i] if all_data.get("metadatas") else {}
                doc_date = meta.get("document_date", "")
                if doc_date >= since_date:
                    date_results.append({
                        "id": doc_id,
                        "document": all_data["documents"][i] if all_data.get("documents") else "",
                        "metadata": meta,
                        "distance": 0,
                    })
                    seen_ids.add(doc_id)
        
        # Also get semantic results and merge (avoiding duplicates)
        semantic_results = semantic_search(question, config, n_results=n_chunks)
        for r in semantic_results:
            if r["id"] not in seen_ids:
                date_results.append(r)
                seen_ids.add(r["id"])
        
        # Deduplicate by title — keep first chunk per document for breadth
        title_seen = {}
        deduped = []
        for r in date_results:
            title = r["metadata"].get("title", "Unknown")
            if title not in title_seen:
                title_seen[title] = 0
            title_seen[title] += 1
            # Keep up to 2 chunks per document
            if title_seen[title] <= 2:
                deduped.append(r)
        
        results = deduped[:n_chunks * 2]  # Allow more chunks for date queries
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
