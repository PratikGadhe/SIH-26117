"""
Tool 1: Knowledge Search for VYASA.
Wraps the local ChromaDB RAG subsystem into the standardized tool contract.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, Optional

current_dir = os.path.dirname(os.path.abspath(__file__))
agents_root = os.path.abspath(os.path.join(current_dir, ".."))
if agents_root not in sys.path:
    sys.path.insert(0, agents_root)

from tools.base import BaseTool, ToolResult
import rag_tool


class KnowledgeSearchTool(BaseTool):
    """
    Approved tool for searching local organization documents and manuals.
    """

    name = "knowledge_search"
    description = (
        "Search the local organizational knowledge base (ChromaDB) for relevant Standard "
        "Operating Procedures (SOPs), refinery manuals, safety limits, and technical standards."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Target search query string for knowledge retrieval.",
            },
            "top_k": {
                "type": "integer",
                "description": "Maximum number of relevant source snippets to retrieve (1 to 10).",
                "default": 3,
            },
        },
        "required": ["query"],
    }

    def execute(self, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query")
        if not query or not isinstance(query, str) or not query.strip():
            return ToolResult.failure_result(
                self.name,
                "INVALID_QUERY",
                "Query parameter must be a non-empty string.",
            )

        query = query.strip()
        top_k = kwargs.get("top_k", 3)
        try:
            top_k = int(top_k)
            if top_k < 1:
                top_k = 1
            elif top_k > 10:
                top_k = 10
        except (ValueError, TypeError):
            top_k = 3

        try:
            rag_output = rag_tool.rag_tool(query=query, top_k=top_k)
            results = rag_output.get("results", [])
            context = rag_output.get("context", "")

            # Extract structured citation objects
            citations = []
            for item in results:
                citations.append(
                    {
                        "source": item.get("source", "Unknown"),
                        "page": str(item.get("page", "N/A")),
                        "distance": item.get("distance"),
                    }
                )

            return ToolResult.success_result(
                self.name,
                result={
                    "query": query,
                    "results_count": len(results),
                    "results": results,
                    "context": context,
                    "citations": citations,
                },
                metadata={
                    "engine": rag_output.get(
                        "engine", "ChromaDB + SentenceTransformers"
                    ),
                    "top_k": top_k,
                },
            )

        except rag_tool.RAGUnavailableError as e:
            return ToolResult.failure_result(
                self.name,
                "RAG_UNAVAILABLE",
                f"Knowledge retrieval service is currently unavailable: {str(e)}",
            )
        except Exception as e:
            return ToolResult.failure_result(
                self.name,
                "SEARCH_FAILED",
                f"Knowledge search failed: {str(e)}",
            )
