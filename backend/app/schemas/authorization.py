"""Schemas used by the RBAC demonstration endpoints."""

from typing import Literal

from pydantic import BaseModel

from app.core.roles import Role


class AuthorizationDemoResponse(BaseModel):
    """Confirmation that an explicit role policy allowed access."""

    status: Literal["authorized"] = "authorized"
    role: Role
    policy: Literal["admin-only", "operations"]
