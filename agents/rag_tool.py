"""
RAG Tool Module for SIH 26117 Agents
Bridges Member 2's ChromaDB document search into a clean agent tool.
"""

import os
import sys
from typing import Any, Dict, List

# Ensure project root is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def rag_tool(query: str, top_k: int = 3) -> Dict[str, Any]:
    """
    Search MRPL operating manuals, safety SOPs, and threshold limits.

    Args:
        query: The search query string.
        top_k: Number of relevant snippets to retrieve.

    Returns:
        Dictionary with status, results list, and formatted context string.
    """
    # 1. Try importing Member 2's ChromaDB search module
    try:
        rag_src_path = os.path.join(project_root, "rag", "MRPL-Sovereign-AI", "RAG", "src")
        if rag_src_path not in sys.path:
            sys.path.insert(0, rag_src_path)

        from search import search_documents
        raw_results = search_documents(query, top_k=top_k)

        if raw_results:
            formatted_context = "\n\n".join(
                f"[Source: {r.get('source', 'Unknown')} | Page {r.get('page', 'N/A')}]\n{r.get('content', '')}"
                for r in raw_results
            )
            return {
                "status": "success",
                "query": query,
                "results": raw_results,
                "context": formatted_context,
                "engine": "ChromaDB + SentenceTransformers"
            }
    except Exception:
        pass

    # 2. Fallback to base RAGService if ChromaDB is unindexed
    try:
        from rag.rag_service import RAGService
        rag = RAGService()
        base_res = rag.query(query, top_k=top_k)
        return {
            "status": "success",
            "query": query,
            "results": base_res.get("results", []),
            "context": base_res.get("answer", "No context available."),
            "engine": "RAGService (Memory fallback)"
        }
    except Exception as e:
        return {
            "status": "error",
            "query": query,
            "error": str(e),
            "results": [],
            "context": ""
        }
