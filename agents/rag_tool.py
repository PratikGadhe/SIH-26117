"""
RAG Tool Module for SIH 26117 Agents.

Bridges the local ChromaDB document search into a clean
agent-friendly interface.
"""

from collections.abc import Callable
from functools import lru_cache
import importlib.util
import os
from pathlib import Path
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

RAGSearch = Callable[..., list[dict[str, Any]]]


class RAGUnavailableError(RuntimeError):
    """Raised when the real document retrieval subsystem cannot run."""


def rag_tool(
    query: str,
    top_k: int = 3,
    *,
    search: RAGSearch | None = None,
) -> Dict[str, Any]:
    """
    Search the local MRPL knowledge base.

    Args:
        query: The search query string.
        top_k: Number of relevant snippets to retrieve.

    Returns:
        Dictionary containing search results and formatted context.
    """
    try:
        raw_results = (search or _load_rag_search())(query, top_k=top_k)
        clean_results = _normalize_results(raw_results)

        formatted_context = "\n\n".join(
            f"[Source: {result.get('source', 'Unknown')} | "
            f"Page {result.get('page', 'N/A')}]\n"
            f"{result.get('content', '')}"
            for result in clean_results
        )

        return {
            "status": "success",
            "query": query,
            "results": clean_results,
            "context": formatted_context,
            "engine": "ChromaDB + SentenceTransformers",
        }

    except RAGUnavailableError:
        raise
    except Exception as exc:
        raise RAGUnavailableError("RAG retrieval is unavailable") from exc


@lru_cache(maxsize=1)
def _load_rag_search() -> RAGSearch:
    if rag_src_path not in sys.path:
        sys.path.insert(0, rag_src_path)

    interface_path = Path(rag_src_path) / "rag_interface.py"
    if not interface_path.is_file():
        raise RAGUnavailableError("RAG interface is unavailable")

    spec = importlib.util.spec_from_file_location(
        "cognivault_rag_interface",
        interface_path,
    )
    if spec is None or spec.loader is None:
        raise RAGUnavailableError("RAG interface cannot be loaded")

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except (ImportError, ModuleNotFoundError) as exc:
        raise RAGUnavailableError("RAG dependencies are unavailable") from exc

    search = getattr(module, "search_documents_for_agent", None)
    if not callable(search):
        raise RAGUnavailableError("RAG interface is invalid")
    return search


def _normalize_results(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise RAGUnavailableError("RAG returned an invalid result")

    results: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        source = (
            str(item.get("source", "Unknown"))
            .replace("\\", "/")
            .rsplit("/", 1)[-1]
        )
        page = item.get("page", "N/A")
        distance = item.get("distance")
        results.append(
            {
                "content": content,
                "source": source or "Unknown",
                "page": page,
                "distance": (
                    distance
                    if isinstance(distance, (int, float))
                    else None
                ),
            }
        )
    return results
