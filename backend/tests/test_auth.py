import asyncio
from datetime import timedelta
from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response
import jwt
import pytest

from app.core.config import Settings
from app.core.roles import Role
from app.core.security import create_access_token, verify_password
from app.db.database import connect_database, initialize_database
from app.db.users import get_user_by_username, set_user_active
from app.main import create_app

TEST_JWT_SECRET = "phase-2-test-secret-that-is-at-least-32-characters"
VALID_CREDENTIALS = {
    "username": "engineer",
    "password": "correct horse battery staple",
}


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "auth.db",
        jwt_secret=TEST_JWT_SECRET,
        jwt_expiration_minutes=30,
    )


@pytest.fixture
def test_app(settings: Settings) -> FastAPI:
    initialize_database(settings.database_path)
    return create_app(settings)


async def send_request(
    application: FastAPI,
    method: str,
    path: str,
    **kwargs: object,
) -> Response:
    transport = ASGITransport(app=application)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        return await client.request(method, path, **kwargs)


def register(application: FastAPI) -> Response:
    return asyncio.run(
        send_request(
            application,
            "POST",
            "/api/v1/auth/register",
            json=VALID_CREDENTIALS,
        )
    )


def login(application: FastAPI, **credentials: str) -> Response:
    payload = {**VALID_CREDENTIALS, **credentials}
    return asyncio.run(
        send_request(
            application,
            "POST",
            "/api/v1/auth/login",
            json=payload,
        )
    )


def authorization_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_valid_registration_hashes_password_and_returns_safe_user(
    test_app: FastAPI,
    settings: Settings,
) -> None:
    response = register(test_app)

    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "engineer"
    assert body["is_active"] is True
    assert body["role"] == "user"
    assert "password" not in body
    assert "password_hash" not in body

    with connect_database(settings.database_path) as connection:
        stored_user = get_user_by_username(connection, "engineer")
    assert stored_user is not None
    assert stored_user.password_hash != VALID_CREDENTIALS["password"]
    assert stored_user.password_hash.startswith("$argon2id$")
    assert verify_password(
        VALID_CREDENTIALS["password"],
        stored_user.password_hash,
    )


def test_registration_validates_credentials(test_app: FastAPI) -> None:
    response = asyncio.run(
        send_request(
            test_app,
            "POST",
            "/api/v1/auth/register",
            json={"username": "   ", "password": "short"},
        )
    )

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


@pytest.mark.parametrize("privileged_role", ["admin", "officer", "worker"])
def test_registration_cannot_self_assign_a_privileged_role(
    test_app: FastAPI,
    settings: Settings,
    privileged_role: str,
) -> None:
    response = asyncio.run(
        send_request(
            test_app,
            "POST",
            "/api/v1/auth/register",
            json={**VALID_CREDENTIALS, "role": privileged_role},
        )
    )

    assert response.status_code == 422
    with connect_database(settings.database_path) as connection:
        assert get_user_by_username(connection, "engineer") is None


def test_duplicate_registration_fails(test_app: FastAPI) -> None:
    assert register(test_app).status_code == 201

    response = register(test_app)

    assert response.status_code == 409
    assert response.json() == {"detail": "Username is already registered"}


def test_login_with_correct_credentials_returns_token(test_app: FastAPI) -> None:
    register(test_app)

    response = login(test_app)

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["expires_in"] == 1800
    assert response.json()["access_token"]


@pytest.mark.parametrize(
    ("credentials"),
    [
        {"password": "incorrect password"},
        {"username": "unknown-user"},
    ],
)
def test_invalid_login_does_not_reveal_user_state(
    test_app: FastAPI,
    credentials: dict[str, str],
) -> None:
    register(test_app)

    response = login(test_app, **credentials)

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid username or password"}


def test_inactive_user_cannot_login(
    test_app: FastAPI,
    settings: Settings,
) -> None:
    user_id = register(test_app).json()["id"]
    with connect_database(settings.database_path) as connection:
        set_user_active(connection, user_id, False)

    response = login(test_app)

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid username or password"}


def test_valid_token_authenticates_current_user(test_app: FastAPI) -> None:
    register(test_app)
    token = login(test_app).json()["access_token"]

    response = asyncio.run(
        send_request(
            test_app,
            "GET",
            "/api/v1/auth/me",
            headers=authorization_header(token),
        )
    )

    assert response.status_code == 200
    assert response.json()["username"] == "engineer"
    assert response.json()["role"] == Role.USER.value
    assert "password" not in response.json()
    assert "password_hash" not in response.json()


def test_missing_token_is_rejected(test_app: FastAPI) -> None:
    response = asyncio.run(
        send_request(test_app, "GET", "/api/v1/auth/me")
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("token", ["not-a-jwt", "one.two.three"])
def test_malformed_token_is_rejected(test_app: FastAPI, token: str) -> None:
    response = asyncio.run(
        send_request(
            test_app,
            "GET",
            "/api/v1/auth/me",
            headers=authorization_header(token),
        )
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Could not validate credentials"}


def test_token_with_invalid_signature_is_rejected(test_app: FastAPI) -> None:
    invalid_token = jwt.encode(
        {"sub": "1", "iat": 1, "exp": 4_102_444_800, "type": "access"},
        "a-different-secret-that-is-at-least-32-characters",
        algorithm="HS256",
    )

    response = asyncio.run(
        send_request(
            test_app,
            "GET",
            "/api/v1/auth/me",
            headers=authorization_header(invalid_token),
        )
    )

    assert response.status_code == 401


def test_expired_token_is_rejected(
    test_app: FastAPI,
    settings: Settings,
) -> None:
    user_id = register(test_app).json()["id"]
    token = create_access_token(
        user_id,
        settings,
        expires_delta=timedelta(seconds=-1),
    )

    response = asyncio.run(
        send_request(
            test_app,
            "GET",
            "/api/v1/auth/me",
            headers=authorization_header(token),
        )
    )

    assert response.status_code == 401


def test_deleted_user_token_is_rejected(
    test_app: FastAPI,
    settings: Settings,
) -> None:
    user_id = register(test_app).json()["id"]
    token = create_access_token(user_id, settings)
    with connect_database(settings.database_path) as connection:
        connection.execute("DELETE FROM users WHERE id = ?", (user_id,))
        connection.commit()

    response = asyncio.run(
        send_request(
            test_app,
            "GET",
            "/api/v1/auth/me",
            headers=authorization_header(token),
        )
    )

    assert response.status_code == 401


def test_inactive_user_token_is_rejected(
    test_app: FastAPI,
    settings: Settings,
) -> None:
    user_id = register(test_app).json()["id"]
    token = create_access_token(user_id, settings)
    with connect_database(settings.database_path) as connection:
        set_user_active(connection, user_id, False)

    response = asyncio.run(
        send_request(
            test_app,
            "GET",
            "/api/v1/auth/me",
            headers=authorization_header(token),
        )
    )

    assert response.status_code == 401
