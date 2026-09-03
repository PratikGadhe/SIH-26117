import asyncio
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response
import pytest

from app.core.audit import AuditEventType
from app.core.config import Settings
from app.core.roles import Role
from app.core.security import create_access_token, hash_password
from app.db.audit import insert_audit_record, list_audit_records
from app.db.database import connect_database, initialize_database
from app.db.users import create_user, get_user_by_username
from app.main import create_app

TEST_JWT_SECRET = "phase-4-test-secret-that-is-at-least-32-characters"
TEST_PASSWORD = "audit-sensitive-password"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "audit.db",
        jwt_secret=TEST_JWT_SECRET,
    )


@pytest.fixture
def test_app(settings: Settings) -> FastAPI:
    initialize_database(settings.database_path)
    return create_app(settings)


async def send_request(
    application: FastAPI,
    method: str,
    path: str,
    *,
    payload: dict[str, str] | None = None,
    token: str | None = None,
) -> Response:
    transport = ASGITransport(app=application)
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        return await client.request(
            method,
            path,
            json=payload,
            headers=headers,
        )


def register(application: FastAPI, username: str = "engineer") -> Response:
    return asyncio.run(
        send_request(
            application,
            "POST",
            "/api/v1/auth/register",
            payload={"username": username, "password": TEST_PASSWORD},
        )
    )


def login(
    application: FastAPI,
    username: str = "engineer",
    password: str = TEST_PASSWORD,
) -> Response:
    return asyncio.run(
        send_request(
            application,
            "POST",
            "/api/v1/auth/login",
            payload={"username": username, "password": password},
        )
    )


def provision_token(settings: Settings, role: Role) -> tuple[int, str]:
    with connect_database(settings.database_path) as connection:
        user = create_user(
            connection,
            f"{role.value}-auditor",
            "unused-password-hash",
            role=role,
        )
    return user.id, create_access_token(user.id, settings)


def read_events(settings: Settings) -> list:
    with connect_database(settings.database_path) as connection:
        return list_audit_records(connection, limit=100, offset=0)


def test_audit_records_can_be_inserted_and_queried(settings: Settings) -> None:
    initialize_database(settings.database_path)
    created_at = datetime.now(timezone.utc)
    with connect_database(settings.database_path) as connection:
        insert_audit_record(
            connection,
            created_at=created_at,
            event_type=AuditEventType.AUTH_LOGIN_FAILURE,
            user_id=None,
            username="engineer",
            success=False,
            resource="/api/v1/auth/login",
            action="POST",
            ip_address=None,
            details={"reason": "invalid_credentials"},
        )
        records = list_audit_records(connection, limit=10, offset=0)

    assert len(records) == 1
    assert records[0].event_type is AuditEventType.AUTH_LOGIN_FAILURE
    assert records[0].created_at == created_at
    assert records[0].details == {"reason": "invalid_credentials"}


def test_registration_success_is_audited(
    test_app: FastAPI,
    settings: Settings,
) -> None:
    response = register(test_app)

    assert response.status_code == 201
    records = read_events(settings)
    assert len(records) == 1
    record = records[0]
    assert record.event_type is AuditEventType.AUTH_REGISTER_SUCCESS
    assert record.user_id == response.json()["id"]
    assert record.username == "engineer"
    assert record.success is True
    assert record.resource == "/api/v1/auth/register"
    assert record.action == "POST"
    assert record.details == {}


def test_login_success_and_failure_are_audited(
    test_app: FastAPI,
    settings: Settings,
) -> None:
    register(test_app)

    success = login(test_app)
    failure = login(test_app, password="incorrect-password")

    assert success.status_code == 200
    assert failure.status_code == 401
    records = read_events(settings)
    by_type = {record.event_type: record for record in records}
    success_record = by_type[AuditEventType.AUTH_LOGIN_SUCCESS]
    failure_record = by_type[AuditEventType.AUTH_LOGIN_FAILURE]
    assert success_record.user_id is not None
    assert success_record.success is True
    assert success_record.details == {}
    assert failure_record.user_id is None
    assert failure_record.success is False
    assert failure_record.details == {"reason": "invalid_credentials"}


def test_authorization_denial_is_audited_once(
    test_app: FastAPI,
    settings: Settings,
) -> None:
    user_id, token = provision_token(settings, Role.USER)

    response = asyncio.run(
        send_request(
            test_app,
            "GET",
            "/api/v1/authorization-demo/admin",
            token=token,
        )
    )

    assert response.status_code == 403
    records = read_events(settings)
    assert len(records) == 1
    record = records[0]
    assert record.event_type is AuditEventType.AUTHORIZATION_DENIED
    assert record.user_id == user_id
    assert record.details == {
        "role": "user",
        "required_roles": ["admin"],
    }


@pytest.mark.parametrize(
    ("role", "expected_status"),
    [
        (Role.ADMIN, 200),
        (Role.OFFICER, 403),
        (Role.WORKER, 403),
        (Role.USER, 403),
    ],
)
def test_only_admin_can_query_audit_records(
    test_app: FastAPI,
    settings: Settings,
    role: Role,
    expected_status: int,
) -> None:
    _, token = provision_token(settings, role)

    response = asyncio.run(
        send_request(test_app, "GET", "/api/v1/audit", token=token)
    )

    assert response.status_code == expected_status


@pytest.mark.parametrize("token", [None, "invalid-token"])
def test_audit_query_requires_valid_authentication(
    test_app: FastAPI,
    token: str | None,
) -> None:
    response = asyncio.run(
        send_request(test_app, "GET", "/api/v1/audit", token=token)
    )

    assert response.status_code == 401


def test_audit_query_filters_paginates_and_orders_newest_first(
    test_app: FastAPI,
    settings: Settings,
) -> None:
    admin_id, token = provision_token(settings, Role.ADMIN)
    now = datetime.now(timezone.utc)
    with connect_database(settings.database_path) as connection:
        for index, event_type in enumerate(
            (
                AuditEventType.AUTH_REGISTER_SUCCESS,
                AuditEventType.AUTH_LOGIN_FAILURE,
                AuditEventType.AUTH_LOGIN_FAILURE,
            )
        ):
            insert_audit_record(
                connection,
                created_at=now + timedelta(seconds=index),
                event_type=event_type,
                user_id=admin_id,
                username="admin-auditor",
                success=event_type is AuditEventType.AUTH_REGISTER_SUCCESS,
                resource="/test",
                action="GET",
                ip_address=None,
                details={},
            )

    response = asyncio.run(
        send_request(
            test_app,
            "GET",
            "/api/v1/audit?limit=1&offset=1"
            "&event_type=AUTH_LOGIN_FAILURE"
            f"&user_id={admin_id}",
            token=token,
        )
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["event_type"] == "AUTH_LOGIN_FAILURE"
    assert datetime.fromisoformat(response.json()[0]["created_at"]) == (
        now + timedelta(seconds=1)
    )


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1"])
def test_audit_query_rejects_unsafe_pagination(
    test_app: FastAPI,
    settings: Settings,
    query: str,
) -> None:
    _, token = provision_token(settings, Role.ADMIN)

    response = asyncio.run(
        send_request(
            test_app,
            "GET",
            f"/api/v1/audit?{query}",
            token=token,
        )
    )

    assert response.status_code == 422


def test_stored_audit_data_excludes_sensitive_authentication_values(
    test_app: FastAPI,
    settings: Settings,
) -> None:
    register(test_app)
    login_response = login(test_app)
    token = login_response.json()["access_token"]
    login(test_app, password="submitted-wrong-password")

    with connect_database(settings.database_path) as connection:
        user = get_user_by_username(connection, "engineer")
        rows = connection.execute("SELECT * FROM audit_events").fetchall()
    assert user is not None
    serialized = json.dumps([dict(row) for row in rows], sort_keys=True)
    for sensitive_value in (
        TEST_PASSWORD,
        "submitted-wrong-password",
        user.password_hash,
        token,
        f"Bearer {token}",
        TEST_JWT_SECRET,
    ):
        assert sensitive_value not in serialized
    assert "password_hash" not in serialized


def test_audit_failure_does_not_bypass_authorization(
    test_app: FastAPI,
    settings: Settings,
) -> None:
    _, token = provision_token(settings, Role.USER)
    with connect_database(settings.database_path) as connection:
        connection.execute("DROP TABLE audit_events")
        connection.commit()

    response = asyncio.run(
        send_request(
            test_app,
            "GET",
            "/api/v1/authorization-demo/admin",
            token=token,
        )
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient permissions"}
