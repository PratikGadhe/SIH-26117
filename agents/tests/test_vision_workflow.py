"""Focused tests for the Vision path through the existing agent workflow."""

import importlib
from pathlib import Path

import pytest

from agents.src import nodes

vision_module = importlib.import_module("vision_tool")


class StubVisionService:
    def __init__(self, result: dict) -> None:
        self.result = result
        self.calls = []

    def analyze_image(self, image_path: str, prompt: str) -> dict:
        self.calls.append((image_path, prompt))
        return self.result

    def analyze_pdf_document(self, pdf_path: str, prompt: str) -> dict:
        self.calls.append((pdf_path, prompt))
        return self.result


def test_vision_tool_calls_existing_service(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    image_path = tmp_path / "diagram.png"
    image_path.touch()
    service = StubVisionService(
        {
            "status": "success",
            "analysis": "Pump A is operating normally.",
            "confidence": 0.9,
            "structured": {"equipment": "Pump A"},
            "raw_response": "private model output",
        }
    )

    monkeypatch.setattr(vision_module, "VisionService", lambda: service)
    result = vision_module.vision_tool(str(image_path), "Inspect the pump")

    assert service.calls == [(str(image_path), "Inspect the pump")]
    assert result["analysis"] == "Pump A is operating normally."
    assert result["confidence"] == 0.9
    assert result["structured"] == {"equipment": "Pump A"}


def test_vision_node_stores_result_for_downstream_nodes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "diagram.png"
    image_path.touch()
    expected = {
        "status": "success",
        "analysis": "Pump A is operating normally.",
        "confidence": 0.9,
    }
    monkeypatch.setattr(nodes, "vision_tool", lambda path, prompt: expected)

    result = nodes.vision_node(
        {
            "user_query": "Inspect this pump",
            "image_path": str(image_path),
            "pdf_path": None,
            "steps_log": [],
        }
    )

    assert result["vision_data"] == expected
    assert result["steps_log"][0]["agent"] == "Vision Agent (Qwen3-VL)"


def test_vision_node_calls_vision_service_through_real_tool(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "diagram.png"
    image_path.touch()
    service = StubVisionService(
        {
            "status": "success",
            "analysis": "Valve B is closed.",
            "confidence": 0.84,
        }
    )
    monkeypatch.setattr(vision_module, "VisionService", lambda: service)

    result = nodes.vision_node(
        {
            "user_query": "Inspect this valve",
            "image_path": str(image_path),
            "pdf_path": None,
            "steps_log": [],
        }
    )

    assert service.calls == [(str(image_path), "Inspect this valve")]
    assert result["vision_data"]["analysis"] == "Valve B is closed."
    assert result["vision_data"]["confidence"] == 0.84


def test_hybrid_rag_receives_vision_analysis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []
    monkeypatch.setattr(
        nodes,
        "rag_tool",
        lambda query, top_k=3: calls.append((query, top_k))
        or {
            "status": "success",
            "results": [],
            "context": "SOP context",
        },
    )

    result = nodes.rag_node(
        {
            "user_query": "Is this pump compliant with the SOP?",
            "vision_data": {
                "status": "success",
                "analysis": "Pump A is operating normally.",
                "confidence": 0.9,
            },
            "steps_log": [],
        }
    )

    assert calls == [
        (
            "Is this pump compliant with the SOP? Pump A is operating normally.",
            3,
        )
    ]
    assert result["rag_data"]["context"] == "SOP context"


def test_vision_failure_is_controlled_by_agent_service(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "diagram.png"
    image_path.touch()
    monkeypatch.setattr(
        nodes,
        "vision_tool",
        lambda path, prompt: (_ for _ in ()).throw(
            RuntimeError("Vision service is unavailable")
        ),
    )

    with pytest.raises(RuntimeError, match="Vision service is unavailable"):
        nodes.vision_node(
            {
                "user_query": "Inspect this pump",
                "image_path": str(image_path),
                "pdf_path": None,
                "steps_log": [],
            }
        )