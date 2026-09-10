"""System status endpoint reporting verified runtime availability."""

from typing import Literal
from fastapi import APIRouter
import httpx
from pydantic import BaseModel

from app.api.dependencies import CurrentUser

router = APIRouter(prefix="/system", tags=["system status"])


class ComponentStatus(BaseModel):
    status: Literal["online", "offline", "available", "unavailable"]


class ModelAvailability(BaseModel):
    available: bool


class ModelsStatus(BaseModel):
    qwen3_4b: ModelAvailability
    qwen3_vl_4b: ModelAvailability


class SystemStatusResponse(BaseModel):
    backend: ComponentStatus
    ollama: ComponentStatus
    models: ModelsStatus
    local_processing: bool


async def probe_ollama(
    base_url: str = "http://localhost:11434",
) -> tuple[bool, bool, bool]:
    """Probe local Ollama tags endpoint and check model availability.

    Returns: (ollama_available, qwen3_4b_available, qwen3_vl_4b_available)
    """
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{base_url}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                model_names = [
                    m.get("name", "").lower() for m in data.get("models", [])
                ]
                qwen3_4b = any(
                    "qwen3:4b" in m or ("qwen3" in m and "4b" in m and "vl" not in m)
                    for m in model_names
                )
                qwen3_vl = any(
                    "qwen3-vl" in m or ("qwen3" in m and "vl" in m) for m in model_names
                )
                return True, qwen3_4b, qwen3_vl
    except Exception:
        pass
    return False, False, False


@router.get(
    "/status", response_model=SystemStatusResponse, summary="Get system runtime status"
)
async def system_status(_: CurrentUser) -> SystemStatusResponse:
    """Return truthful status of the backend, local Ollama runtime, and models."""
    ollama_ok, qwen3_4b_ok, qwen3_vl_ok = await probe_ollama()

    return SystemStatusResponse(
        backend=ComponentStatus(status="online"),
        ollama=ComponentStatus(status="available" if ollama_ok else "unavailable"),
        models=ModelsStatus(
            qwen3_4b=ModelAvailability(available=qwen3_4b_ok),
            qwen3_vl_4b=ModelAvailability(available=qwen3_vl_ok),
        ),
        local_processing=True,
    )
