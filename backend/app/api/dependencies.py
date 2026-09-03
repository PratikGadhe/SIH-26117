"""Reusable FastAPI dependencies."""

from collections.abc import Callable
from typing import Annotated
import sqlite3

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings
from app.core.roles import Role
from app.core.security import AuthenticationConfigurationError
from app.core.security import InvalidAccessTokenError, decode_access_token
from app.db.database import get_database
from app.db.users import User, get_user_by_id
from app.services.audit import record_authorization_denied
from app.services.agent import AgentService

bearer_scheme = HTTPBearer(auto_error=False)

DatabaseConnection = Annotated[sqlite3.Connection, Depends(get_database)]
BearerCredentials = Annotated[
    HTTPAuthorizationCredentials | None,
    Security(bearer_scheme),
]


def get_settings(request: Request) -> Settings:
    """Return this application instance's immutable settings."""

    return request.app.state.settings


SettingsDependency = Annotated[Settings, Depends(get_settings)]


def get_agent_service(request: Request) -> AgentService:
    """Return the backend-owned service wrapping the configured agent."""

    return request.app.state.agent_service


AgentServiceDependency = Annotated[AgentService, Depends(get_agent_service)]


def get_current_user(
    credentials: BearerCredentials,
    connection: DatabaseConnection,
    settings: SettingsDependency,
) -> User:
    """Resolve and validate the user represented by a bearer token."""

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _authentication_error()

    try:
        user_id = decode_access_token(credentials.credentials, settings)
    except AuthenticationConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        ) from exc
    except InvalidAccessTokenError as exc:
        raise _authentication_error() from exc

    user = get_user_by_id(connection, user_id)
    if user is None or not user.is_active:
        raise _authentication_error()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*allowed_roles: Role) -> Callable[..., User]:
    """Create a dependency requiring one of the explicitly allowed roles."""

    if not allowed_roles:
        raise ValueError("At least one allowed role is required")
    allowed = frozenset(allowed_roles)

    def authorize_role(
        user: CurrentUser,
        request: Request,
        connection: DatabaseConnection,
    ) -> User:
        if user.role not in allowed:
            record_authorization_denied(
                connection,
                user_id=user.id,
                username=user.username,
                role=user.role,
                required_roles=allowed,
                resource=request.url.path,
                action=request.method,
                ip_address=get_client_ip(request),
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return authorize_role


def get_client_ip(request: Request) -> str | None:
    """Read the direct peer address without trusting forwarded headers."""

    return request.client.host if request.client is not None else None


def _authentication_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
