import json

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
