"""Health-check endpoint."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Response returned when the application is healthy."""

    status: Literal["ok"]


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Report whether the application is running."""

    return HealthResponse(status="ok")
