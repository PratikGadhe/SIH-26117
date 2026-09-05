import json

from PIL import Image

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


def test_analyze_image_calls_ollama_and_returns_structured_result(tmp_path):
    image_path = tmp_path / "inspection.png"
    Image.new("RGB", (40, 40), "white").save(image_path)

    class StubClient:
        def generate_with_vision(self, **kwargs):
            assert kwargs["image_path"] == str(image_path)
            return '{"equipment": "Pump A", "confidence": 0.95}'

    service = VisionService.__new__(VisionService)
    service.client = StubClient()

    result = service.analyze_image(str(image_path), "Inspect the equipment")

    assert result["status"] == "success"
    assert result["model"] == "qwen3-vl:4b"
    assert result["structured"] == {
        "equipment": "Pump A",
        "confidence": 0.95,
    }


def test_analyze_image_rejects_invalid_image(tmp_path):
    image_path = tmp_path / "invalid.png"
    image_path.write_text("not an image")

    service = VisionService.__new__(VisionService)
    result = service.analyze_image(str(image_path), "Inspect the equipment")

    assert result["status"] == "error"
    assert result["error"].startswith("Invalid image:")


def test_pdf_document_method_creates_standard_result_shape():
    service = VisionService.__new__(VisionService)
    result = service.analyze_pdf_document("sample.pdf", "Extract all text and key values")

    assert "status" in result
    assert "pages" in result
    assert "model" in result
