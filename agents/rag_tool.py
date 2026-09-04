"""
RAG Tool Module for SIH 26117 Agents.

Bridges the local ChromaDB document search into a clean
agent-friendly interface.
"""

import os
import sys
from typing import Any, Dict


# Locate the RAG source directory.
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
rag_src_path = os.path.join(
    project_root,
    "rag",
    "MRPL-Sovereign-AI",
    "RAG",
    "src",
)

if rag_src_path not in sys.path:
    sys.path.insert(0, rag_src_path)

from search import search_documents


def rag_tool(query: str, top_k: int = 3) -> Dict[str, Any]:
    """
    Search the local MRPL knowledge base.

    Args:
        query: The search query string.
        top_k: Number of relevant snippets to retrieve.

    Returns:
        Dictionary containing search results and formatted context.
    """
    try:
        raw_results = search_documents(query, top_k=top_k)

        formatted_context = "\n\n".join(
            f"[Source: {result.get('source', 'Unknown')} | "
            f"Page {result.get('page', 'N/A')}]\n"
            f"{result.get('content', '')}"
            for result in raw_results
        )

        return {
            "status": "success",
            "query": query,
            "results": raw_results,
            "context": formatted_context,
            "engine": "ChromaDB + SentenceTransformers",
        }

    except Exception as exc:
        return {
            "status": "error",
            "query": query,
            "results": [],
            "context": "",
            "engine": "ChromaDB + SentenceTransformers",
            "error": str(exc),
        }