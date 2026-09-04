"""Authentication request and response schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from app.core.roles import Role


class CredentialsRequest(BaseModel):
    """Shared local username and password input."""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=64)
    password: SecretStr = Field(min_length=8, max_length=256)

    @field_validator("username")
    @classmethod
    def username_must_not_be_blank(cls, value: str) -> str:
        username = value.strip()
        if not username:
            raise ValueError("Username must not be blank")
        return username


class RegisterRequest(CredentialsRequest):
    """Input used to create a local user."""


class LoginRequest(CredentialsRequest):
    """Input used to authenticate a local user."""


class UserResponse(BaseModel):
    """Safe public representation of a user."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    is_active: bool
    role: Role
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    """JWT access-token response."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(gt=0)
