"""Small endpoints demonstrating reusable role authorization."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import require_roles
from app.core.roles import Role
from app.db.users import User
from app.schemas.authorization import AuthorizationDemoResponse

router = APIRouter(
    prefix="/authorization-demo",
    tags=["authorization demonstration"],
)

AdminUser = Annotated[User, Depends(require_roles(Role.ADMIN))]
OperationsUser = Annotated[
    User,
    Depends(require_roles(Role.ADMIN, Role.OFFICER, Role.WORKER)),
]


@router.get("/admin", response_model=AuthorizationDemoResponse)
def admin_only(user: AdminUser) -> AuthorizationDemoResponse:
    """Demonstrate a policy that explicitly allows only administrators."""

    return AuthorizationDemoResponse(role=user.role, policy="admin-only")


@router.get("/operations", response_model=AuthorizationDemoResponse)
def operations(user: OperationsUser) -> AuthorizationDemoResponse:
    """Demonstrate explicit operational role access without role hierarchy."""

    return AuthorizationDemoResponse(role=user.role, policy="operations")
