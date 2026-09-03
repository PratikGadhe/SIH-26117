from pathlib import Path
from typing import Any, Dict, List, Optional

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


def route_vision_task(
    prompt: str,
    image_path: Optional[str] = None,
    document_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Dispatch an agent request to the appropriate local vision operation."""
    path = document_path or image_path
    if not path:
        return {"status": "error", "error": "An image_path or document_path is required"}

    if Path(path).suffix.lower() == ".pdf":
        return pdf_tool(path, prompt)
    return vision_tool(path, prompt)
