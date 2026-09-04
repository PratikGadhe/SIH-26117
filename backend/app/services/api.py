"""Services for API metadata."""

from app.schemas.api import ApiInfoResponse


def get_api_info() -> ApiInfoResponse:
    """Return metadata for the active API version."""

    return ApiInfoResponse(name="Cognivault API", version="v1")
