"""
Vision Service Module for SIH 26117
Core vision analysis using Qwen3-VL
Exposes a simple interface: analyze_image(image, prompt)
"""

import io
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

from PIL import Image

from .ollama_client import OllamaClient

try:
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover
    fitz = None

try:
    import pytesseract
except Exception:  # pragma: no cover
    pytesseract = None


class VisionService:
    """
    Multimodal vision service using Qwen3-VL.

    Public interface:
        analyze_image(image_path, prompt) -> dict
        extract_text_from_image(image_path) -> str
        analyze_drawing(image_path) -> dict
        analyze_pdf_document(pdf_path, prompt) -> dict
        analyze_multi_image(image_paths, prompt) -> dict
    """

    def __init__(self, ollama_base_url: str = "http://localhost:11434"):
        """
        Initialize vision service

        Args:
            ollama_base_url: Ollama API endpoint
        """
        self.client = OllamaClient(ollama_base_url)

        if not self.client.is_available():
            raise RuntimeError(
                "❌ Ollama service not running. Start Ollama with: ollama serve"
            )

        print("✅ Vision Service initialized with Qwen3-VL 4B")
        print(f"📊 Model info: {self.client.get_model_info()}")

    def analyze_image(
        self,
        image_path: str,
        prompt: str,
        return_json: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze an image using Qwen3-VL vision model.
        """
        try:
            if not image_path or not Path(image_path).exists():
                return {
                    "status": "error",
                    "error": f"Image not found: {image_path}",
                    "image_path": str(image_path),
                    "prompt": prompt,
                }

            response = self.client.generate_with_vision(
                prompt=prompt,
                image_path=image_path,
                temperature=0.5,
                top_p=0.9,
            )
            analysis = response.strip()
            confidence = self._extract_confidence(analysis)

            result = {
                "status": "success",
                "analysis": analysis,
                "confidence": confidence,
                "image_path": str(image_path),
                "prompt": prompt,
                "model": "qwen3-vl:4b",
                "raw_response": analysis,
            }

            if return_json:
                structured = self.parse_structured_response(analysis)
                if isinstance(structured, dict):
                    result["structured"] = structured

            return result

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "image_path": str(image_path),
                "prompt": prompt,
            }

    def extract_text_from_image(self, image_path: str) -> str:
        """
        Extract text from scanned documents or images (OCR).
        """
        if not image_path or not Path(image_path).exists():
            raise RuntimeError(f"Image not found: {image_path}")

        # Prefer a real OCR engine when available, then fall back to vision model.
        if pytesseract is not None:
            try:
                text = pytesseract.image_to_string(Image.open(image_path))
                if text and text.strip():
                    return text.strip()
            except Exception:
                pass

        prompt = """
        Please extract ALL text from this image exactly as it appears.
        Include main text, labels, numbers, headers, annotations and handwritten notes.
        Return the extracted text only, with line breaks preserved.
        """

        result = self.analyze_image(image_path, prompt)
        if result["status"] == "success":
            return result["analysis"]
        raise RuntimeError(f"OCR failed: {result.get('error')}")

    def analyze_drawing(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze engineering drawing or schematic.
        """
        prompt = """
        Analyze this engineering drawing or schematic. Provide:

        1. Drawing Type
        2. Main Components
        3. Connections
        4. Labels and part numbers
        5. Dimensions/specifications
        6. Notes and warnings
        7. Condition

        Format as a structured list and be specific.
        """
        return self.analyze_image(image_path, prompt)

    def analyze_handwritten_document(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze handwritten notes or signatures.
        """
        prompt = """
        This appears to be a handwritten document. Please:

        1. Transcribe all handwritten text exactly
        2. Identify document type
        3. Note signatures or initials
        4. Identify date if present
        5. Flag unclear or ambiguous text
        6. Preserve formatting
        """
        return self.analyze_image(image_path, prompt)

    def analyze_industrial_equipment(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze industrial scenes, machine panels, instruments and equipment.
        """
        prompt = """
        Inspect this industrial equipment image. Identify:
        - Equipment type and model if visible
        - Operating status and readings
        - Components and labels
        - Safety warnings or alarm states
        - Maintenance or inspection issues
        - Recommended next action

        Return a concise but detailed technical assessment.
        """
        return self.analyze_image(image_path, prompt)

    def analyze_pdf_document(
        self,
        pdf_path: str,
        prompt: str = "Extract all readable text and key values from this document.",
    ) -> Dict[str, Any]:
        """
        Read a PDF and extract page-level text, using PyMuPDF when available.
        """
        if not pdf_path or not Path(pdf_path).exists():
            return {
                "status": "error",
                "error": f"PDF not found: {pdf_path}",
                "pdf_path": str(pdf_path),
                "prompt": prompt,
                "pages": [],
                "page_count": 0,
                "model": "qwen3-vl:4b",
            }

        pages: List[Dict[str, Any]] = []
        extracted_text: List[str] = []

        if fitz is not None:
            try:
                doc = fitz.open(pdf_path)
                for page_index in range(doc.page_count):
                    page = doc[page_index]
                    page_text = page.get_text("text").strip()
                    extracted_text.append(page_text)
                    pages.append({
                        "page": page_index + 1,
                        "text": page_text,
                        "chars": len(page_text),
                    })
                doc.close()
            except Exception as exc:  # pragma: no cover
                pages = []
                extracted_text = [str(exc)]

        combined_text = "\n\n".join(part for part in extracted_text if part)

        if not combined_text.strip():
            combined_text = "No text found in PDF via native extraction."

        return {
            "status": "success",
            "model": "qwen3-vl:4b",
            "pdf_path": str(pdf_path),
            "prompt": prompt,
            "pages": pages,
            "text": combined_text,
            "confidence": 0.8,
            "page_count": len(pages),
        }

    def analyze_multpage_document(
        self,
        pdf_path: str,
        prompt: str = "Analyze this multi-page document and summarize the content, keys and technical details.",
    ) -> Dict[str, Any]:
        """
        Alias for multi-page document understanding.
        """
        return self.analyze_pdf_document(pdf_path, prompt)

    def analyze_multi_image(
        self,
        image_paths: Iterable[str],
        prompt: str,
    ) -> Dict[str, Any]:
        """
        Analyze multiple images together and return a combined result.
        """
        items = list(image_paths)
        if not items:
            return {"status": "error", "error": "No images provided"}

        analyses = []
        for image_path in items:
            if not Path(image_path).exists():
                analyses.append({"image_path": str(image_path), "status": "error", "error": "Image not found"})
                continue
            analyses.append(self.analyze_image(image_path, prompt))

        combined_text = "\n\n".join(
            item.get("analysis", "") for item in analyses if item.get("status") == "success"
        )

        return {
            "status": "success",
            "model": "qwen3-vl:4b",
            "prompt": prompt,
            "images": items,
            "results": analyses,
            "combined_analysis": combined_text or "No summary available",
            "confidence": self._extract_confidence(combined_text) if combined_text else 0.0,
        }

    @staticmethod
    def parse_structured_response(response: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Parse a JSON-like response into a dictionary for structured output.
        """
        if isinstance(response, dict):
            return response

        text = str(response or "").strip()
        if not text:
            return {}

        stripped = text.replace("```json", "").replace("```", "").strip()
        if not stripped:
            return {}

        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        return {"raw_response": text}

    def extract_structured_json(
        self,
        image_path: str,
        prompt: str,
        schema_name: str = "analysis",
    ) -> Dict[str, Any]:
        """
        Extract and normalize model output into structured JSON payload.
        """
        result = self.analyze_image(image_path, prompt)
        if result["status"] != "success":
            return {
                "status": "error",
                "error": result.get("error"),
                "image_path": str(image_path),
                "prompt": prompt,
            }

        structured = self.parse_structured_response(result["analysis"])
        return {
            "status": "success",
            "schema_name": schema_name,
            "data": structured,
            "confidence": result.get("confidence", 0.7),
            "model": "qwen3-vl:4b",
            "raw_response": result.get("analysis", ""),
        }

    @staticmethod
    def _extract_confidence(response: str) -> float:
        """Extract confidence score from response if present."""
        try:
            patterns = [
                r'confidence[:\s]+([0-9.]+)',
                r'confidence\s*=\s*([0-9]+)%',
            ]

            for pattern in patterns:
                match = re.search(pattern, str(response).lower())
                if match:
                    value = float(match.group(1))
                    if value > 1.0:
                        value = value / 100.0
                    return min(1.0, max(0.0, value))

            return 0.7
        except Exception:
            return 0.7
