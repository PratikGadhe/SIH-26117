from typing import Any, Dict
import sys
import os

RAG_SRC = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "rag",
        "MRPL-Sovereign-AI",
        "RAG",
        "src"
    )
)

if RAG_SRC not in sys.path:
    sys.path.insert(0, RAG_SRC)

from search import search_documents


def rag_tool(query: str, top_k: int = 3) -> Dict[str, Any]:
    """Search the local MRPL knowledge base and return agent-friendly results."""

    try:
        results = search_documents(query, top_k=top_k)

        sources = []

        for result in results:
            sources.append({
                "content": result["content"],
                "source": result["source"],
                "page": result["page"],
                "distance": result["distance"]
            })

        return {
            "status": "success",
            "query": query,
            "results": sources
        }

    except Exception as exc:
        return {
            "status": "error",
            "query": query,
            "results": [],
            "error": str(exc)
        }