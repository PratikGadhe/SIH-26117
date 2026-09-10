"""Tests for the system status endpoint."""

import asyncio
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response
import pytest

from app.core.config import Settings
from app.core.roles import Role
from app.core.security import create_access_token
from app.db.database import connect_database, initialize_database
from app.db.users import create_user
from app.main import create_app

TEST_JWT_SECRET = "system-status-test-secret-key-that-is-long-enough-for-hs256"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "system_test.db",
        jwt_secret=TEST_JWT_SECRET,
    )


@pytest.fixture
def test_app(settings: Settings) -> FastAPI:
    initialize_database(settings.database_path)
    return create_app(settings)


def provision_token(settings: Settings, role: Role = Role.WORKER) -> str:
    with connect_database(settings.database_path) as connection:
        user = create_user(
            connection,
            "status-test-user",
            "unused-hash",
            role=role,
        )
    return create_access_token(user.id, settings)


async def send_status_request(
    application: FastAPI,
    token: str | None = None,
) -> Response:
    transport = ASGITransport(app=application)
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        return await client.get("/api/v1/system/status", headers=headers)


def test_system_status_unauthorized_without_token(test_app: FastAPI) -> None:
    response = asyncio.run(send_status_request(test_app, token=None))
    assert response.status_code == 401


def test_system_status_authorized_returns_valid_schema(
    test_app: FastAPI, settings: Settings
) -> None:
    token = provision_token(settings)
    response = asyncio.run(send_status_request(test_app, token=token))
    assert response.status_code == 200
    data = response.json()
    assert data["backend"]["status"] == "online"
    assert data["ollama"]["status"] in ("available", "unavailable")
    assert "qwen3_4b" in data["models"]
    assert "qwen3_vl_4b" in data["models"]
    assert data["local_processing"] is True


def test_system_status_with_mocked_ollama_online(
    test_app: FastAPI, settings: Settings
) -> None:
    token = provision_token(settings)

    mock_models = (True, True, True)  # ollama_ok, qwen3_4b_ok, qwen3_vl_ok
    with patch("app.api.system.probe_ollama", return_value=mock_models):
        response = asyncio.run(send_status_request(test_app, token=token))

    assert response.status_code == 200
    data = response.json()
    assert data["backend"]["status"] == "online"
    assert data["ollama"]["status"] == "available"
    assert data["models"]["qwen3_4b"]["available"] is True
    assert data["models"]["qwen3_vl_4b"]["available"] is True
    assert data["local_processing"] is True


def test_system_status_with_mocked_ollama_offline(
    test_app: FastAPI, settings: Settings
) -> None:
    token = provision_token(settings)

    mock_models = (False, False, False)
    with patch("app.api.system.probe_ollama", return_value=mock_models):
        response = asyncio.run(send_status_request(test_app, token=token))

    assert response.status_code == 200
    data = response.json()
    assert data["backend"]["status"] == "online"
    assert data["ollama"]["status"] == "unavailable"
    assert data["models"]["qwen3_4b"]["available"] is False
    assert data["models"]["qwen3_vl_4b"]["available"] is False
    assert data["local_processing"] is True
