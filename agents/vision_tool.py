"""Lazy, agent-facing adapter for the teammate-owned vision service."""

from collections.abc import Callable
from functools import lru_cache
import importlib
from pathlib import Path
from typing import Any, Dict, Iterable, List, NoReturn, Optional, Protocol


class VisionServiceContract(Protocol):
    def analyze_image(
        self,
        image_path: str,
        prompt: str,
    ) -> Dict[str, Any]: ...

    def analyze_pdf_document(
        self,
        pdf_path: str,
        prompt: str,
    ) -> Dict[str, Any]: ...

    def analyze_multi_image(
        self,
        image_paths: Iterable[str],
        prompt: str,
    ) -> Dict[str, Any]: ...


VisionServiceFactory = Callable[[], VisionServiceContract]


class VisionIntegrationError(RuntimeError):
    """Base class for safe vision-boundary failures."""


class VisionInputError(VisionIntegrationError):
    """Raised when a referenced vision input is invalid."""


class VisionUnavailableError(VisionIntegrationError):
    """Raised when vision dependencies or the local model are unavailable."""


class VisionExecutionError(VisionIntegrationError):
    """Raised when the vision service cannot produce a usable result."""


def vision_tool(
    image_path: str,
    prompt: str,
    *,
    service: VisionServiceContract | None = None,
) -> Dict[str, Any]:
    _validate_file(image_path, expected_suffix=None)
    result = _invoke(
        lambda: (service or _get_vision_service()).analyze_image(
            image_path,
            prompt,
        )
    )
    return _normalize_analysis(result)


def pdf_tool(
    pdf_path: str,
    prompt: str = "Extract all readable text and key values.",
    *,
    service: VisionServiceContract | None = None,
) -> Dict[str, Any]:
    _validate_file(pdf_path, expected_suffix=".pdf")
    result = _invoke(
        lambda: (service or _get_vision_service()).analyze_pdf_document(
            pdf_path,
            prompt,
        )
    )
    pages = result.get("pages")
    if isinstance(pages, list):
        for page in pages:
            if isinstance(page, dict) and page.get("error"):
                _raise_service_failure(str(page["error"]))

    page_count = result.get("page_count")
    if not isinstance(page_count, int) or page_count <= 0:
        raise VisionExecutionError("Vision document processing failed")

    normalized = _normalize_analysis(result, analysis_field="text")
    normalized["page_count"] = page_count
    return normalized


def multi_image_tool(
    image_paths: List[str],
    prompt: str,
    *,
    service: VisionServiceContract | None = None,
) -> Dict[str, Any]:
    if not image_paths:
        raise VisionInputError("Vision input is invalid")
    for image_path in image_paths:
        _validate_file(image_path, expected_suffix=None)

    result = _invoke(
        lambda: (service or _get_vision_service()).analyze_multi_image(
            image_paths,
            prompt,
        )
    )
    items = result.get("results")
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict) and item.get("status") != "success":
                _raise_service_failure(str(item.get("error", "")))
    return _normalize_analysis(result, analysis_field="combined_analysis")


def route_vision_task(
    prompt: str,
    image_path: Optional[str] = None,
    document_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Dispatch an agent request to the appropriate local vision operation."""

    path = document_path or image_path
    if not path:
        raise VisionInputError("Vision input is invalid")

    if Path(path).suffix.lower() == ".pdf":
        return pdf_tool(path, prompt)
    return vision_tool(path, prompt)


@lru_cache(maxsize=1)
def _load_vision_service() -> VisionServiceFactory:
    try:
        module = importlib.import_module("vision.src.vision_service")
    except Exception as exc:
        raise VisionUnavailableError("Vision dependencies are unavailable") from exc

    service_factory = getattr(module, "VisionService", None)
    if not callable(service_factory):
        raise VisionUnavailableError("Vision interface is invalid")
    return service_factory


@lru_cache(maxsize=1)
def _get_vision_service() -> VisionServiceContract:
    try:
        return _load_vision_service()()
    except VisionIntegrationError:
        raise
    except Exception as exc:
        _raise_service_failure(str(exc), cause=exc)


def _validate_file(path: str, expected_suffix: str | None) -> None:
    candidate = Path(path)
    if not candidate.is_file():
        raise VisionInputError("Vision input is invalid")
    if expected_suffix is not None and candidate.suffix.lower() != expected_suffix:
        raise VisionInputError("Vision input is invalid")


def _invoke(operation: Callable[[], object]) -> Dict[str, Any]:
    try:
        result = operation()
    except VisionIntegrationError:
        raise
    except TimeoutError as exc:
        raise TimeoutError("Vision inference timed out") from exc
    except Exception as exc:
        _raise_service_failure(str(exc), cause=exc)

    if not isinstance(result, dict):
        raise VisionExecutionError("Vision returned an invalid result")
    if result.get("status") != "success":
        _raise_service_failure(str(result.get("error", "")))
    return result


def _normalize_analysis(
    result: Dict[str, Any],
    *,
    analysis_field: str = "analysis",
) -> Dict[str, Any]:
    analysis = result.get(analysis_field)
    if not isinstance(analysis, str) or not analysis.strip():
        raise VisionExecutionError("Vision returned no usable analysis")
    if analysis.strip() == "No text found in PDF via native extraction.":
        raise VisionExecutionError("Vision returned no usable analysis")

    confidence = result.get("confidence")
    normalized: Dict[str, Any] = {
        "status": "success",
        "analysis": analysis.strip(),
        "confidence": (
            float(confidence)
            if isinstance(confidence, (int, float))
            else None
        ),
    }
    structured = result.get("structured")
    if isinstance(structured, dict):
        normalized["structured"] = structured
    return normalized


def _raise_service_failure(
    error: str,
    *,
    cause: Exception | None = None,
) -> NoReturn:
    normalized = error.lower()
    if "timeout" in normalized or "timed out" in normalized:
        raise TimeoutError("Vision inference timed out") from cause
    if any(
        marker in normalized
        for marker in (
            "ollama",
            "model",
            "not running",
            "connection refused",
            "unavailable",
        )
    ):
        raise VisionUnavailableError("Vision service is unavailable") from cause
    raise VisionExecutionError("Vision execution failed") from cause
