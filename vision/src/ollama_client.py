"""
Ollama API wrapper for Qwen3-VL model
Handles connection, image encoding, and inference
"""

import base64
import json
import re
import requests
from typing import Optional
from pathlib import Path


class OllamaClient:
    """Wrapper around Ollama API for vision model inference"""

    def __init__(self, base_url: str = "http://localhost:11434"):
        """
        Initialize Ollama client

        Args:
            base_url: Ollama API endpoint (default: localhost:11434)
        """
        self.base_url = base_url
        self.model = "qwen3-vl:4b"
        self.api_endpoint = f"{base_url}/api/generate"

    def is_available(self) -> bool:
        """Check if Ollama service is running"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Ollama not available: {e}")
            return False

    def encode_image(self, image_path: str) -> str:
        """
        Encode image to base64 for API submission

        Args:
            image_path: Path to image file

        Returns:
            Base64 encoded string
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def generate_with_vision(
        self,
        prompt: str,
        image_path: Optional[str] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> str:
        """
        Generate response using Qwen3-VL with optional image

        Args:
            prompt: Text prompt/question
            image_path: Path to image file (optional)
            temperature: Model temperature (0.0-1.0)
            top_p: Nucleus sampling parameter

        Returns:
            Generated response text
        """
        # Build the request
        request_data = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "temperature": temperature,
            "top_p": top_p,
        }

        # Add image if provided
        if image_path:
            if not Path(image_path).exists():
                raise FileNotFoundError(f"Image not found: {image_path}")

            # Encode image to base64
            image_b64 = self.encode_image(image_path)

            # Ollama expects images in the 'images' field as list of base64 strings
            request_data["images"] = [image_b64]

        try:
            # Increase timeout for vision inference (can be slow on first run)
            response = requests.post(
                self.api_endpoint,
                json=request_data,
                timeout=300,  # 5 minutes for vision inference
            )
            response.raise_for_status()

            result = response.json()
            raw_resp = result.get("response", "").strip()
            resp_text = re.sub(
                r"<think>.*?</think>", "", raw_resp, flags=re.DOTALL
            ).strip()
            if not resp_text and "thinking" in result:
                resp_text = re.sub(
                    r"<think>.*?</think>",
                    "",
                    result.get("thinking", ""),
                    flags=re.DOTALL,
                ).strip()
            return resp_text

        except requests.exceptions.Timeout:
            raise TimeoutError(
                "Ollama inference timed out (>5 min). Check GPU memory and ensure Ollama is responsive."
            )
        except Exception as e:
            raise RuntimeError(f"Inference failed: {e}")

    def get_model_info(self) -> dict:
        """Get information about the loaded model"""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            data = response.json()

            for model in data.get("models", []):
                if model["name"] == self.model:
                    return model

            return {}
        except Exception as e:
            print(f"Could not fetch model info: {e}")
            return {}
