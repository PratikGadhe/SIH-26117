import asyncio
from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response
import pytest

from app.api.dependencies import require_roles
from app.core.config import Settings
from app.core.roles import Role
from app.core.security import create_access_token
from app.db.database import connect_database, initialize_database
from app.db.users import create_user
from app.main import create_app

TEST_JWT_SECRET = "phase-3-test-secret-that-is-at-least-32-characters"


def test_role_enum_rejects_unknown_values() -> None:
    with pytest.raises(ValueError):
        Role("superadmin")


def test_authorization_policy_requires_at_least_one_role() -> None:
    with pytest.raises(ValueError):
        require_roles()


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "rbac.db",
        jwt_secret=TEST_JWT_SECRET,
    )


@pytest.fixture
def test_app(settings: Settings) -> FastAPI:
    initialize_database(settings.database_path)
    return create_app(settings)


async def send_request(
    application: FastAPI,
    path: str,
    token: str | None = None,
) -> Response:
    transport = ASGITransport(app=application)
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        return await client.get(path, headers=headers)


def provision_token(settings: Settings, role: Role) -> str:
    with connect_database(settings.database_path) as connection:
        user = create_user(
            connection,
            f"{role.value}-account",
            "unused-password-hash",
            role=role,
        )
    return create_access_token(user.id, settings)


@pytest.mark.parametrize(
    ("role", "path", "expected_status"),
    [
        (Role.ADMIN, "/api/v1/authorization-demo/admin", 200),
        (Role.ADMIN, "/api/v1/authorization-demo/operations", 200),
        (Role.OFFICER, "/api/v1/authorization-demo/admin", 403),
        (Role.OFFICER, "/api/v1/authorization-demo/operations", 200),
        (Role.WORKER, "/api/v1/authorization-demo/admin", 403),
        (Role.WORKER, "/api/v1/authorization-demo/operations", 200),
        (Role.USER, "/api/v1/authorization-demo/admin", 403),
        (Role.USER, "/api/v1/authorization-demo/operations", 403),
    ],
)
def test_explicit_role_policies(
    test_app: FastAPI,
    settings: Settings,
    role: Role,
    path: str,
    expected_status: int,
) -> None:
    token = provision_token(settings, role)

    response = asyncio.run(send_request(test_app, path, token))

    assert response.status_code == expected_status
    if expected_status == 200:
        assert response.json()["status"] == "authorized"
        assert response.json()["role"] == role.value
    else:
        assert response.json() == {"detail": "Insufficient permissions"}


def test_missing_token_is_unauthenticated_not_forbidden(
    test_app: FastAPI,
) -> None:
    response = asyncio.run(
        send_request(test_app, "/api/v1/authorization-demo/admin")
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_invalid_token_is_unauthenticated_not_forbidden(
    test_app: FastAPI,
) -> None:
    response = asyncio.run(
        send_request(
            test_app,
            "/api/v1/authorization-demo/admin",
            "invalid-token",
        )
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Could not validate credentials"}
