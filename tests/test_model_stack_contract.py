from backend.text_service import TextOllamaClient
from rag.rag_service import RAGService
from agents.text_tool import text_tool


def test_text_client_has_required_model_fields():
    client = TextOllamaClient(model_name="qwen3:4b")
    assert client.model_name == "qwen3:4b"
    assert client.base_url == "http://localhost:11434"


def test_rag_service_has_query_interface():
    rag = RAGService()
    assert hasattr(rag, "add_documents")
    assert hasattr(rag, "query")


def test_agent_tool_returns_dict():
    result = text_tool("Explain the project in one sentence.")
    assert isinstance(result, dict)
    assert "status" in result
