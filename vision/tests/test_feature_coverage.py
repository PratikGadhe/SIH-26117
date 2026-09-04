import json

import pytest
from PIL import Image, ImageDraw

try:
    import fitz
except ImportError:  # pragma: no cover
    fitz = None

from vision.src.vision_service import VisionService


def test_core_multimodal_methods_exist():
    service = VisionService.__new__(VisionService)

    required_methods = [
        "analyze_image",
        "extract_text_from_image",
        "analyze_drawing",
        "analyze_handwritten_document",
        "analyze_pdf_document",
        "analyze_multi_image",
        "extract_structured_json",
    ]

    for name in required_methods:
        assert hasattr(service, name), f"Missing required method: {name}"


def test_structured_json_parser_handles_json_payload():
    payload = '{"equipment": [{"name": "Pump A", "status": "ok"}], "confidence": 0.92}'
    parsed = VisionService.parse_structured_response(payload)

    assert isinstance(parsed, dict)
    assert parsed["equipment"][0]["name"] == "Pump A"
    assert parsed["confidence"] == 0.92


def test_pdf_document_method_creates_standard_result_shape():
    service = VisionService.__new__(VisionService)
    result = service.analyze_pdf_document("sample.pdf", "Extract all text and key values")

    assert "status" in result
    assert "pages" in result
    assert "model" in result


@pytest.mark.skipif(fitz is None, reason="PyMuPDF is not installed")
def test_scanned_pdf_page_is_sent_to_vision_model(tmp_path):
    image = Image.new("RGB", (240, 100), "white")
    ImageDraw.Draw(image).text((10, 35), "Pump A - OK", fill="black")
    image_path = tmp_path / "scanned-page.png"
    image.save(image_path)

    pdf_path = tmp_path / "scanned.pdf"
    document = fitz.open()
    page = document.new_page(width=240, height=100)
    page.insert_image(page.rect, filename=str(image_path))
    document.save(pdf_path)
    document.close()

    service = VisionService.__new__(VisionService)
    calls = []

    def fake_analyze(image_path, prompt, return_json=True):
        calls.append((image_path, prompt, return_json))
        return {
            "status": "success",
            "analysis": "Pump A - OK",
            "structured": {"equipment": "Pump A"},
            "confidence": 0.9,
        }

    service.analyze_image = fake_analyze
    result = service.analyze_pdf_document(str(pdf_path), "Read this scanned page")

    assert result["status"] == "success"
    assert result["pages"][0]["source"] == "vision_model"
    assert result["pages"][0]["analysis"] == "Pump A - OK"
    assert len(calls) == 1


def test_pdf_and_image_tasks_are_routed(monkeypatch):
    import agents.vision_tool as vision_tool_module

    calls = []
    monkeypatch.setattr(
        vision_tool_module,
        "pdf_tool",
        lambda path, prompt: calls.append(("pdf", path, prompt)) or {"status": "success"},
    )
    monkeypatch.setattr(
        vision_tool_module,
        "vision_tool",
        lambda path, prompt: calls.append(("image", path, prompt)) or {"status": "success"},
    )

    assert vision_tool_module.route_vision_task("read", document_path="report.pdf")["status"] == "success"
    assert vision_tool_module.route_vision_task("inspect", image_path="drawing.png")["status"] == "success"
    assert calls == [("pdf", "report.pdf", "read"), ("image", "drawing.png", "inspect")]
