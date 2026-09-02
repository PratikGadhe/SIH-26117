from typing import Any, Dict

from backend.text_service import TextOllamaClient


def text_tool(prompt: str, model_name: str = "qwen3:4b") -> Dict[str, Any]:
    client = TextOllamaClient(model_name=model_name)

    if not client.is_available():
        return {
            "status": "error",
            "model": model_name,
            "prompt": prompt,
            "error": "Ollama service is not running. Use: ollama serve",
        }

    try:
        response = client.generate(prompt)
        return {
            "status": "success",
            "model": model_name,
            "prompt": prompt,
            "answer": response,
        }
    except Exception as exc:  # pragma: no cover
        return {
            "status": "error",
            "model": model_name,
            "prompt": prompt,
            "error": str(exc),
        }
