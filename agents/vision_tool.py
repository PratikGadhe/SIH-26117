from typing import Any, Dict, List

from vision.src.vision_service import VisionService


def vision_tool(image_path: str, prompt: str) -> Dict[str, Any]:
    service = VisionService()
    return service.analyze_image(image_path, prompt)


def pdf_tool(pdf_path: str, prompt: str = "Extract all readable text and key values.") -> Dict[str, Any]:
    service = VisionService()
    return service.analyze_pdf_document(pdf_path, prompt)


def multi_image_tool(image_paths: List[str], prompt: str) -> Dict[str, Any]:
    service = VisionService()
    return service.analyze_multi_image(image_paths, prompt)
