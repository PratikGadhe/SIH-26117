"""
Ollama Text & Reasoning Client for SIH 26117
Handles text inference, structured JSON output, and local connection to Qwen on Apple Silicon Metal.
"""

import json
import re
import time
import requests
from typing import Optional, Dict, Any, Union


def strip_reasoning_and_thinking(text: str) -> str:
    """
    Cleans model generation output by stripping internal reasoning:
    1. Removes <think>...</think> blocks (including multiline and unclosed tags).
    2. Strips internal reasoning preamble lines (e.g. "First, the user asked...").
    3. Returns clean user-facing response text.
    """
    if not text:
        return ""

    # Strip <think>...</think> blocks
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    if "<think>" in cleaned and "</think>" not in cleaned:
        cleaned = re.sub(r"<think>.*$", "", cleaned, flags=re.DOTALL)
    cleaned = cleaned.replace("</think>", "").strip()

    # Strip conversational reasoning preamble lines
    lines = cleaned.splitlines()
    filtered_lines = []
    skipping_meta = True
    meta_starters = (
        "first, the user asked",
        "first, i need",
        "first, i should",
        "first, i must",
        "i need to base",
        "i should base",
        "i must base",
        "the rule says",
        "the rules state",
        "the rule states",
        "let me check",
        "let me see",
        "i should not add",
        "i must not add",
        "the user is asking",
        "the user asks",
        "the response should be",
        "looking at the visual",
        "based on the rules",
    )
    for line in lines:
        stripped = line.strip().lower()
        if skipping_meta and any(stripped.startswith(m) for m in meta_starters):
            continue
        skipping_meta = False
        filtered_lines.append(line)

    if filtered_lines:
        cleaned = "\n".join(filtered_lines).strip()

    return cleaned


class OllamaTextClient:
    """
    Client for interacting with local Ollama text/reasoning models (e.g. qwen3:4b, qwen2.5:3b, qwen2.5:7b).
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model_name: str = "qwen3:4b",
        timeout: int = 300,
    ):
        """
        Initialize the local Ollama text client.

        Args:
            base_url: The local Ollama server address.
            model_name: Target model tag (default: qwen3:4b).
            timeout: Max timeout for inference in seconds.
        """
        self.base_url = base_url.rstrip("/")
        self.model = model_name
        self.timeout = timeout
        self.api_generate_url = f"{self.base_url}/api/generate"
        self.api_tags_url = f"{self.base_url}/api/tags"

    def is_available(self) -> bool:
        """Check if the local Ollama daemon is running."""
        try:
            res = requests.get(self.api_tags_url, timeout=3)
            return res.status_code == 200
        except Exception:
            return False

    def list_local_models(self) -> list:
        """Return a list of all model names currently available in local Ollama."""
        try:
            res = requests.get(self.api_tags_url, timeout=3)
            if res.status_code == 200:
                data = res.json()
                return [m.get("name", "") for m in data.get("models", [])]
            return []
        except Exception:
            return []

    def get_model_info(self) -> Dict[str, Any]:
        """Fetch details about the configured model."""
        try:
            models = self.list_local_models()
            for m in models:
                if self.model in m:
                    return {"model": m, "status": "available"}
            return {
                "model": self.model,
                "status": "not_found",
                "available_models": models,
            }
        except Exception as e:
            return {"error": str(e)}

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        top_p: float = 0.9,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate text completion from the local Qwen model.

        Args:
            prompt: User message / query.
            system_prompt: Optional system instruction setting the AI's persona.
            temperature: Randomness (0.0 to 1.0, lower is better for engineering facts).
            top_p: Nucleus sampling probability.
            max_tokens: Optional cap on generated tokens.
            stream: Whether to stream tokens (False for standard request).

        Returns:
            Dictionary with response text, generation time, and token metrics.
        """
        if not self.is_available():
            return {
                "status": "error",
                "error": "Ollama service is not running. Please run 'brew services start ollama' or 'ollama serve'.",
            }

        options_dict = {"temperature": temperature, "top_p": top_p}
        if max_tokens:
            options_dict["num_predict"] = max_tokens
        else:
            options_dict["num_predict"] = 1024

        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            "options": options_dict,
        }

        if system_prompt:
            payload["system"] = system_prompt

        # Bound generation length so local Apple Silicon inference finishes promptly
        limit = max_tokens if max_tokens is not None else 2048
        payload["options"]["num_predict"] = limit

        start_time = time.time()
        try:
            response = requests.post(
                self.api_generate_url, json=payload, timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            elapsed_time = round(time.time() - start_time, 2)

            # Response hygiene: prioritize 'response', strip any <think> tags or reasoning leaks
            raw_resp = data.get("response", "").strip()
            resp_text = strip_reasoning_and_thinking(raw_resp)

            return {
                "status": "success",
                "model": self.model,
                "response": resp_text,
                "elapsed_seconds": elapsed_time,
                "eval_count": data.get("eval_count", 0),
                "eval_duration_ns": data.get("eval_duration", 0),
                "tokens_per_second": round(
                    data.get("eval_count", 0) / (data.get("eval_duration", 1) / 1e9), 1
                )
                if data.get("eval_duration")
                else 0,
            }

        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Inference timed out after {self.timeout} seconds.",
            }
        except Exception as e:
            return {"status": "error", "error": f"Inference failed: {str(e)}"}

    def generate_json(
        self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.1
    ) -> Dict[str, Any]:
        """
        Force the model to return valid structured JSON.
        Crucial for LangGraph routing, tool decisions, and task planning.
        """
        if not self.is_available():
            return {"status": "error", "error": "Ollama service is not running."}

        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": temperature, "num_predict": 512},
        }
        if system_prompt:
            payload["system"] = system_prompt

        start_time = time.time()
        try:
            response = requests.post(
                self.api_generate_url, json=payload, timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            elapsed_time = round(time.time() - start_time, 2)

            resp_text = data.get("response", "").strip()
            if not resp_text and "thinking" in data:
                resp_text = data.get("thinking", "").strip()

            clean_text = resp_text.replace("```json", "").replace("```", "").strip()
            parsed_json = json.loads(clean_text)

            return {
                "status": "success",
                "model": self.model,
                "json_data": parsed_json,
                "elapsed_seconds": elapsed_time,
            }
        except json.JSONDecodeError:
            import re

            match = re.search(r"\{.*\}", resp_text, flags=re.DOTALL)
            if match:
                try:
                    return {
                        "status": "success",
                        "model": self.model,
                        "json_data": json.loads(match.group(0)),
                        "elapsed_seconds": elapsed_time,
                    }
                except Exception:
                    pass
            return {"status": "parse_error", "raw_response": resp_text}
        except Exception as e:
            return {"status": "error", "error": str(e)}
