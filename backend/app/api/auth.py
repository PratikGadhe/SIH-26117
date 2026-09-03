"""Local authentication endpoints."""

from fastapi import APIRouter, HTTPException, Request, status

from app.api.dependencies import CurrentUser, DatabaseConnection
from app.api.dependencies import SettingsDependency, get_client_ip
from app.core.security import AuthenticationConfigurationError
from app.db.users import DuplicateUsernameError
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.auth import UserResponse
from app.services.auth import InvalidCredentialsError, login_user, register_user
from app.services.audit import record_login_failure, record_login_success
from app.services.audit import record_registration_success

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: RegisterRequest,
    request: Request,
    connection: DatabaseConnection,
) -> UserResponse:
    """Create a local Cognivault user."""

    try:
        user = register_user(
            connection,
            payload.username,
            payload.password.get_secret_value(),
        )
    except DuplicateUsernameError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already registered",
        ) from exc
    record_registration_success(
        connection,
        user_id=user.id,
        username=user.username,
        resource=request.url.path,
        action=request.method,
        ip_address=get_client_ip(request),
    )
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    connection: DatabaseConnection,
    settings: SettingsDependency,
) -> TokenResponse:
    """Verify local credentials and return a JWT access token."""

    try:
        result = login_user(
            connection,
            settings,
            payload.username,
            payload.password.get_secret_value(),
        )
    except InvalidCredentialsError as exc:
        record_login_failure(
            connection,
            username=payload.username,
            resource=request.url.path,
            action=request.method,
            ip_address=get_client_ip(request),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except AuthenticationConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        ) from exc
    record_login_success(
        connection,
        user_id=result.user.id,
        username=result.user.username,
        resource=request.url.path,
        action=request.method,
        ip_address=get_client_ip(request),
    )
    return result.token


@router.get("/me", response_model=UserResponse)
def current_user(user: CurrentUser) -> UserResponse:
    """Return the authenticated user's safe profile."""

    return UserResponse.model_validate(user)
