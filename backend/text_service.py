from __future__ import annotations

from typing import Any, Dict, Optional

import requests


class TextOllamaClient:
    """Local text-generation client for Ollama-backed models."""

    def __init__(self, model_name: str = "qwen3:4b", base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url

    def is_available(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> str:
        if not self.is_available():
            raise RuntimeError("Ollama service is not running. Start it with: ollama serve")

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "temperature": temperature,
        }

        if max_tokens is not None:
            payload["options"] = {"num_predict": max_tokens}

        response = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=180,
        )
        response.raise_for_status()

        data = response.json()
        return str(data.get("response", "")).strip()

    def chat(self, prompt: str, system_prompt: str = "") -> str:
        return self.generate(prompt=prompt, system_prompt=system_prompt)
