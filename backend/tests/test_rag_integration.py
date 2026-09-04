"""Focused tests for the LangGraph-to-RAG integration boundary."""

import importlib.util
from pathlib import Path
import sys

import pytest

from app.integrations.agent import AgentUnavailableError, LangGraphAgentAdapter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AGENTS_ROOT = PROJECT_ROOT / "agents"
RAG_SOURCE = (
    PROJECT_ROOT / "rag" / "MRPL-Sovereign-AI" / "RAG" / "src"
)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def rag_tool_module():
    return load_module("phase6_rag_tool", AGENTS_ROOT / "rag_tool.py")


def test_rag_tool_normalizes_real_interface_results(rag_tool_module) -> None:
    calls = []

    def search(query: str, top_k: int):
        calls.append((query, top_k))
        return [
            {
                "content": "Emergency shutdown requires valve isolation.",
                "source": "/confidential/storage/shutdown-sop.pdf",
                "page": 7,
                "distance": 0.25,
                "vector": [0.1, 0.2],
            }
        ]

    result = rag_tool_module.rag_tool(
        "emergency shutdown",
        top_k=2,
        search=search,
    )

    assert calls == [("emergency shutdown", 2)]
    assert result == {
        "status": "success",
        "query": "emergency shutdown",
        "results": [
            {
                "content": "Emergency shutdown requires valve isolation.",
                "source": "shutdown-sop.pdf",
                "page": 7,
                "distance": 0.25,
            }
        ],
        "context": (
            "[Source: shutdown-sop.pdf | Page 7]\n"
            "Emergency shutdown requires valve isolation."
        ),
        "engine": "ChromaDB + SentenceTransformers",
    }


def test_rag_tool_resolves_public_rag_interface(
    rag_tool_module,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delitem(sys.modules, "search", raising=False)
    monkeypatch.delitem(sys.modules, "document_processor", raising=False)
    rag_tool_module._load_rag_search.cache_clear()

    search = rag_tool_module._load_rag_search()

    assert callable(search)
    assert "search" not in sys.modules
    assert "document_processor" not in sys.modules


def test_rag_tool_hides_retrieval_failure_details(rag_tool_module) -> None:
    def failing_search(query: str, top_k: int):
        raise RuntimeError("/private/store and confidential database details")

    with pytest.raises(
        rag_tool_module.RAGUnavailableError,
        match="^RAG retrieval is unavailable$",
    ):
        rag_tool_module.rag_tool("private query", search=failing_search)


def test_public_rag_interface_import_is_lightweight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("search", "document_processor"):
        monkeypatch.delitem(sys.modules, name, raising=False)

    module = load_module(
        "phase6_rag_interface",
        RAG_SOURCE / "rag_interface.py",
    )

    assert "search" not in sys.modules
    assert "document_processor" not in sys.modules
    assert callable(module.search_documents_for_agent)
    assert callable(module.process_document_for_agent)


def test_rag_unavailable_result_maps_to_backend_unavailable_error() -> None:
    def workflow(**kwargs):
        return {
            "status": "error",
            "error": "RAG retrieval is unavailable",
        }

    with pytest.raises(AgentUnavailableError):
        LangGraphAgentAdapter(workflow=workflow).run("Check the SOP")
