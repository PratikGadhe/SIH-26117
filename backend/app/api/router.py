"""Versioned API router aggregation."""

from fastapi import APIRouter

from app.api.agent import router as agent_router
from app.api.audit import router as audit_router
from app.api.auth import router as auth_router
from app.api.authorization import router as authorization_router
from app.schemas.api import ApiInfoResponse
from app.services.api import get_api_info

router = APIRouter(prefix="/api/v1", tags=["api"])
router.include_router(auth_router)
router.include_router(authorization_router)
router.include_router(audit_router)
router.include_router(agent_router)


@router.get("", response_model=ApiInfoResponse, summary="Get API information")
async def api_info() -> ApiInfoResponse:
    """Describe the currently available API version."""

    return get_api_info()
