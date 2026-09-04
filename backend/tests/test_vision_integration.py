"""Focused tests for the LangGraph-to-vision integration boundary."""

import importlib.util
from pathlib import Path
import sys

import pytest

from app.integrations.agent import AgentUnavailableError, LangGraphAgentAdapter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VISION_TOOL_PATH = PROJECT_ROOT / "agents" / "vision_tool.py"


def load_vision_tool():
    spec = importlib.util.spec_from_file_location(
        "phase7_vision_tool",
        VISION_TOOL_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StubVisionService:
    def __init__(self, result: dict) -> None:
        self.result = result
        self.calls = []

    def analyze_image(self, image_path: str, prompt: str) -> dict:
        self.calls.append(("image", image_path, prompt))
        return self.result

    def analyze_pdf_document(self, pdf_path: str, prompt: str) -> dict:
        self.calls.append(("pdf", pdf_path, prompt))
        return self.result


def test_vision_tool_import_does_not_load_vision_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in (
        "vision",
        "vision.src",
        "vision.src.vision_service",
        "PIL",
        "requests",
        "fitz",
        "pytesseract",
    ):
        monkeypatch.delitem(sys.modules, name, raising=False)

    module = load_vision_tool()

    assert callable(module.vision_tool)
    assert callable(module.pdf_tool)
    assert "vision.src.vision_service" not in sys.modules
    assert "PIL" not in sys.modules
    assert "requests" not in sys.modules


def test_missing_vision_dependencies_fail_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_vision_tool()

    def missing_module(name: str):
        raise ModuleNotFoundError("private missing dependency detail")

    monkeypatch.setattr(module.importlib, "import_module", missing_module)
    module._load_vision_service.cache_clear()

    with pytest.raises(
        module.VisionUnavailableError,
        match="^Vision dependencies are unavailable$",
    ):
        module._load_vision_service()


def test_image_result_is_normalized_without_raw_state(tmp_path: Path) -> None:
    module = load_vision_tool()
    image_path = tmp_path / "inspection.png"
    image_path.touch()
    service = StubVisionService(
        {
            "status": "success",
            "analysis": "  Pump A is operating normally.  ",
            "confidence": 0.91,
            "image_path": "/confidential/inspection.png",
            "prompt": "confidential prompt",
            "model": "qwen3-vl:4b",
            "raw_response": "private raw model response",
            "tensor": [1, 2, 3],
            "structured": {"equipment": "Pump A"},
        }
    )

    result = module.vision_tool(
        str(image_path),
        "Inspect pump",
        service=service,
    )

    assert service.calls == [("image", str(image_path), "Inspect pump")]
    assert result == {
        "status": "success",
        "analysis": "Pump A is operating normally.",
        "confidence": 0.91,
        "structured": {"equipment": "Pump A"},
    }


def test_pdf_text_is_mapped_to_langgraph_analysis(tmp_path: Path) -> None:
    module = load_vision_tool()
    pdf_path = tmp_path / "inspection.pdf"
    pdf_path.touch()
    service = StubVisionService(
        {
            "status": "success",
            "text": "Page-aware extracted maintenance text",
            "confidence": 0.8,
            "page_count": 2,
            "pages": [{"page": 1, "text": "confidential raw page"}],
            "pdf_path": "/confidential/inspection.pdf",
            "prompt": "private prompt",
        }
    )

    result = module.pdf_tool(str(pdf_path), service=service)

    assert result == {
        "status": "success",
        "analysis": "Page-aware extracted maintenance text",
        "confidence": 0.8,
        "page_count": 2,
    }


def test_pdf_internal_failure_text_is_not_treated_as_analysis(
    tmp_path: Path,
) -> None:
    module = load_vision_tool()
    pdf_path = tmp_path / "broken.pdf"
    pdf_path.touch()
    service = StubVisionService(
        {
            "status": "success",
            "text": "/private/parser/internal failure detail",
            "pages": [],
            "page_count": 0,
        }
    )

    with pytest.raises(
        module.VisionExecutionError,
        match="^Vision document processing failed$",
    ):
        module.pdf_tool(str(pdf_path), service=service)


def test_invalid_input_fails_before_service_initialization(tmp_path: Path) -> None:
    module = load_vision_tool()
    service = StubVisionService({"status": "success", "analysis": "unused"})

    with pytest.raises(module.VisionInputError, match="^Vision input is invalid$"):
        module.vision_tool(str(tmp_path / "missing.png"), "Inspect", service=service)

    assert service.calls == []


@pytest.mark.parametrize(
    ("error", "exception_name", "safe_message"),
    [
        (
            "Ollama service not running at /private/runtime",
            "VisionUnavailableError",
            "Vision service is unavailable",
        ),
        (
            "Inference timed out with internal model details",
            "TimeoutError",
            "Vision inference timed out",
        ),
        (
            "Decoder failed for /confidential/image.png",
            "VisionExecutionError",
            "Vision execution failed",
        ),
    ],
)
def test_vision_failures_are_safe(
    tmp_path: Path,
    error: str,
    exception_name: str,
    safe_message: str,
) -> None:
    module = load_vision_tool()
    image_path = tmp_path / "inspection.png"
    image_path.touch()
    service = StubVisionService({"status": "error", "error": error})
    exception_type = (
        TimeoutError
        if exception_name == "TimeoutError"
        else getattr(module, exception_name)
    )

    with pytest.raises(exception_type, match=f"^{safe_message}$"):
        module.vision_tool(str(image_path), "Inspect", service=service)


def test_vision_unavailable_result_maps_to_backend_unavailable_error() -> None:
    def workflow(**kwargs):
        return {
            "status": "error",
            "error": "Vision service is unavailable",
        }

    with pytest.raises(AgentUnavailableError):
        LangGraphAgentAdapter(workflow=workflow).run("Inspect drawing")
