"""Password hashing and JWT primitives."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError as PyJWTInvalidTokenError

from app.core.config import Settings

password_hasher = PasswordHasher()


class AuthenticationConfigurationError(RuntimeError):
    """Raised when authentication settings are incomplete."""


class InvalidAccessTokenError(ValueError):
    """Raised when an access token cannot be trusted."""


class ExpiredAccessTokenError(InvalidAccessTokenError):
    """Raised when an otherwise valid access token has expired."""


def hash_password(password: str) -> str:
    """Hash a password with Argon2id and a random salt."""

    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Safely verify a password against an Argon2 hash."""

    try:
        return password_hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def create_access_token(
    user_id: int,
    settings: Settings,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token for a user."""

    secret = _require_jwt_secret(settings)
    now = datetime.now(timezone.utc)
    expires_at = now + (
        expires_delta or timedelta(minutes=settings.jwt_expiration_minutes)
    )
    claims = {
        "sub": str(user_id),
        "iat": now,
        "exp": expires_at,
        "iss": "cognivault",
        "type": "access",
    }
    return jwt.encode(claims, secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings) -> int:
    """Validate an access token and return its user ID."""

    secret = _require_jwt_secret(settings)
    try:
        claims = jwt.decode(
            token,
            secret,
            algorithms=[settings.jwt_algorithm],
            issuer="cognivault",
            options={"require": ["sub", "iat", "exp", "type"]},
        )
    except ExpiredSignatureError as exc:
        raise ExpiredAccessTokenError("Access token has expired") from exc
    except PyJWTInvalidTokenError as exc:
        raise InvalidAccessTokenError("Access token is invalid") from exc

    if claims.get("type") != "access":
        raise InvalidAccessTokenError("Token is not an access token")

    try:
        user_id = int(claims["sub"])
    except (TypeError, ValueError) as exc:
        raise InvalidAccessTokenError("Token subject is invalid") from exc

    if user_id <= 0:
        raise InvalidAccessTokenError("Token subject is invalid")
    return user_id


def _require_jwt_secret(settings: Settings) -> str:
    secret = settings.jwt_secret
    if secret is None or len(secret) < 32:
        raise AuthenticationConfigurationError(
            "COGNIVAULT_JWT_SECRET must contain at least 32 characters"
        )
    return secret
