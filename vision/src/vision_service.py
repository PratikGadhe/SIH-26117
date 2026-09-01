"""
Vision Service Module for SIH 26117
Core vision analysis using Qwen3-VL
Exposes a simple interface: analyze_image(image, prompt)
"""

import json
import re
from pathlib import Path
from typing import Optional, Dict, Any
from PIL import Image
import io

from .ollama_client import OllamaClient

class VisionService:
    """
    Multimodal vision service using Qwen3-VL
    
    Public interface:
        analyze_image(image_path, prompt) -> dict
        extract_text_from_image(image_path) -> str
        analyze_drawing(image_path) -> dict
    """
    
    def __init__(self, ollama_base_url: str = "http://localhost:11434"):
        """
        Initialize vision service
        
        Args:
            ollama_base_url: Ollama API endpoint
        """
        self.client = OllamaClient(ollama_base_url)
        
        # Check if Ollama is available
        if not self.client.is_available():
            raise RuntimeError(
                "❌ Ollama service not running. "
                "Start Ollama with: ollama serve"
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
        Analyze an image using Qwen3-VL vision model
        
        Core public interface. Called by Agent (Member 3) and Backend (Member 1).
        
        Args:
            image_path: Path to image file (jpg, png, pdf, etc.)
            prompt: Question or analysis request
            return_json: If True, parse response as JSON
            
        Returns:
            {
                "status": "success" | "error",
                "analysis": "...",
                "confidence": 0.0-1.0,
                "image_path": "...",
                "prompt": "...",
                "model": "qwen3-vl:4b",
                "raw_response": "..."
            }
        """
        
        try:
            # Validate image exists
            if not Path(image_path).exists():
                return {
                    "status": "error",
                    "error": f"Image not found: {image_path}",
                    "image_path": image_path
                }
            
            print(f"🖼️  Analyzing: {Path(image_path).name}")
            print(f"❓ Prompt: {prompt[:100]}...")
            
            # Call Ollama inference
            response = self.client.generate_with_vision(
                prompt=prompt,
                image_path=image_path,
                temperature=0.5,  # Lower temp for more deterministic analysis
                top_p=0.9
            )
            
            # Parse response
            analysis = response.strip()
            
            # Try to extract confidence if model provides it
            confidence = self._extract_confidence(analysis)
            
            result = {
                "status": "success",
                "analysis": analysis,
                "confidence": confidence,
                "image_path": str(image_path),
                "prompt": prompt,
                "model": "qwen3-vl:4b",
                "raw_response": analysis
            }
            
            print(f"✅ Analysis complete (confidence: {confidence:.2f})")
            
            return result
        
        except Exception as e:
            print(f"❌ Analysis failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "image_path": str(image_path),
                "prompt": prompt
            }
    
    def extract_text_from_image(self, image_path: str) -> str:
        """
        Extract text from scanned documents or images (OCR)
        
        Args:
            image_path: Path to image
            
        Returns:
            Extracted text
        """
        prompt = """
        Please extract ALL text from this image exactly as it appears.
        Include:
        - Main text
        - Headers and titles
        - Labels and annotations
        - Numbers and symbols
        - Any handwritten notes
        
        Format the output clearly with line breaks and sections.
        Do not summarize, extract verbatim.
        """
        
        result = self.analyze_image(image_path, prompt)
        
        if result["status"] == "success":
            return result["analysis"]
        else:
            raise RuntimeError(f"OCR failed: {result.get('error')}")
    
    def analyze_drawing(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze engineering drawing or schematic
        
        Args:
            image_path: Path to drawing image
            
        Returns:
            Structured analysis of drawing
        """
        prompt = """
        Analyze this engineering drawing or schematic. Provide:
        
        1. Drawing Type: (P&ID, circuit diagram, blueprint, etc.)
        2. Main Components: List all major elements
        3. Connections: How components connect
        4. Labels: Any text, part numbers, specifications
        5. Dimensions/Specs: Any measurements or values shown
        6. Notes: Any warnings, special instructions
        7. Condition: (clear, faded, damaged, etc.)
        
        Format as structured list. Be precise - this may be used for engineering decisions.
        """
        
        return self.analyze_image(image_path, prompt)
    
    def analyze_handwritten_document(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze handwritten notes or signatures
        
        Args:
            image_path: Path to document image
            
        Returns:
            Transcription and analysis
        """
        prompt = """
        This appears to be a handwritten document. Please:
        
        1. Transcribe all handwritten text exactly
        2. Identify the document type (note, form, approval, signature, etc.)
        3. Note any signatures or initials
        4. Identify date if present
        5. Flag any unclear or ambiguous text
        6. Preserve formatting (bullet points, sections, etc.)
        
        Be thorough and accurate - this may be used for official records.
        """
        
        return self.analyze_image(image_path, prompt)
    
    @staticmethod
    def _extract_confidence(response: str) -> float:
        """
        Extract confidence score from response if present
        
        Args:
            response: Model response text
            
        Returns:
            Confidence between 0.0 and 1.0 (default 0.7)
        """
        try:
            # Look for patterns like "confidence: 0.85" or "confidence=85%"
            patterns = [
                r'confidence[:\s]+([0-9.]+)',
                r'confidence\s*=\s*([0-9]+)%'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, response.lower())
                if match:
                    value = float(match.group(1))
                    # Normalize if percentage
                    if value > 1.0:
                        value = value / 100.0
                    return min(1.0, max(0.0, value))
            
            # Default confidence
            return 0.7
        
        except:
            return 0.7
