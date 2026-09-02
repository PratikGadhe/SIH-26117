"""
Vision Service Module - Member 4 of SIH 26117
Multimodal image analysis using Qwen3-VL 4B
"""

from .vision_service import VisionService
from .ollama_client import OllamaClient

__version__ = "0.1.0"
__all__ = ["VisionService", "OllamaClient"]
