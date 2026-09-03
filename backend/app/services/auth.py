"""Local authentication business logic."""

from __future__ import annotations

from dataclasses import dataclass
import sqlite3

from app.core.config import Settings
from app.core.security import create_access_token, hash_password, password_hasher
from app.core.security import verify_password
from app.db.users import DuplicateUsernameError, User, create_user
from app.db.users import get_user_by_username, update_password_hash
from app.schemas.auth import TokenResponse


class InvalidCredentialsError(ValueError):
    """Raised when local credentials cannot authenticate a user."""


@dataclass(frozen=True)
class LoginResult:
    """Internal authenticated session result."""

    token: TokenResponse
    user: User


def register_user(
    connection: sqlite3.Connection,
    username: str,
    password: str,
) -> User:
    """Hash credentials and persist a new user."""

    normalized_username = username.strip()
    return create_user(
        connection,
        normalized_username,
        hash_password(password),
    )


def login_user(
    connection: sqlite3.Connection,
    settings: Settings,
    username: str,
    password: str,
) -> LoginResult:
    """Verify local credentials and issue an access token."""

    user = get_user_by_username(connection, username.strip())
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError("Invalid username or password")
    if not user.is_active:
        raise InvalidCredentialsError("Invalid username or password")

    if password_hasher.check_needs_rehash(user.password_hash):
        update_password_hash(connection, user.id, hash_password(password))

    return LoginResult(
        token=TokenResponse(
            access_token=create_access_token(user.id, settings),
            expires_in=settings.jwt_expiration_minutes * 60,
        ),
        user=user,
    )


__all__ = [
    "DuplicateUsernameError",
    "InvalidCredentialsError",
    "LoginResult",
    "login_user",
    "register_user",
]
