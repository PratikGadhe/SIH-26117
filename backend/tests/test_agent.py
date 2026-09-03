import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response
import pytest

from app.core.audit import AuditEventType
from app.core.config import Settings
from app.core.roles import Role
from app.core.security import create_access_token
from app.db.audit import insert_audit_record, list_audit_records
from app.db.database import connect_database, initialize_database
from app.db.users import create_user
from app.integrations.agent import AgentCitation, AgentExecutionError
from app.integrations.agent import AgentResult, AgentStep, AgentTimeoutError
from app.integrations.agent import AgentUnavailableError, LangGraphAgentAdapter
from app.main import create_app

TEST_JWT_SECRET = "phase-5-test-secret-that-is-at-least-32-characters"


def successful_result(response: str = "Normalized answer") -> AgentResult:
    return AgentResult(
        response=response,
        task_type="DIRECT_CHAT",
        citations=[AgentCitation(source="manual.pdf", page="4", distance=0.2)],
        steps=[AgentStep(step=1, agent="Supervisor Agent", action="Classified")],
        execution_time_seconds=0.25,
        air_gapped=True,
    )


class FakeAgentRunner:
    def __init__(self, result: AgentResult | None = None) -> None:
        self.result = result or successful_result()
        self.messages: list[str] = []

    def run(self, message: str) -> AgentResult:
        self.messages.append(message)
        return self.result


class FailingAgentRunner:
    def __init__(self, error_type: type[Exception]) -> None:
        self.error_type = error_type

    def run(self, message: str) -> AgentResult:
        raise self.error_type("internal subsystem detail")


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "agent.db",
        jwt_secret=TEST_JWT_SECRET,
    )


@pytest.fixture
def runner() -> FakeAgentRunner:
    return FakeAgentRunner()


@pytest.fixture
def test_app(settings: Settings, runner: FakeAgentRunner) -> FastAPI:
    initialize_database(settings.database_path)
    return create_app(settings, agent_runner=runner)


async def send_request(
    application: FastAPI,
    payload: dict[str, str] | None,
    token: str | None,
) -> Response:
    transport = ASGITransport(app=application)
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        return await client.post(
            "/api/v1/agent/run",
            json=payload,
            headers=headers,
        )


def provision_token(settings: Settings, role: Role) -> tuple[int, str]:
    with connect_database(settings.database_path) as connection:
        user = create_user(
            connection,
            f"{role.value}-agent-user",
            "unused-password-hash",
            role=role,
        )
    return user.id, create_access_token(user.id, settings)


def read_agent_events(settings: Settings) -> list:
    with connect_database(settings.database_path) as connection:
        return list_audit_records(connection, limit=100, offset=0)


@pytest.mark.parametrize("role", [Role.ADMIN, Role.OFFICER, Role.WORKER])
def test_allowed_role_executes_agent(
    test_app: FastAPI,
    settings: Settings,
    runner: FakeAgentRunner,
    role: Role,
) -> None:
    _, token = provision_token(settings, role)

    response = asyncio.run(
        send_request(test_app, {"message": "Inspect the process"}, token)
    )

    assert response.status_code == 200
    assert runner.messages == ["Inspect the process"]
    assert response.json() == {
        "response": "Normalized answer",
        "task_type": "DIRECT_CHAT",
        "citations": [
            {"source": "manual.pdf", "page": "4", "distance": 0.2}
        ],
        "steps": [
            {"step": 1, "agent": "Supervisor Agent", "action": "Classified"}
        ],
        "execution_time_seconds": 0.25,
        "air_gapped": True,
    }


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"message": "   "},
        {"message": "valid", "unsupported": "field"},
        {"message": "x" * 10_001},
    ],
)
def test_agent_request_validation_prevents_execution(
    test_app: FastAPI,
    settings: Settings,
    runner: FakeAgentRunner,
    payload: dict[str, str],
) -> None:
    _, token = provision_token(settings, Role.WORKER)

    response = asyncio.run(send_request(test_app, payload, token))

    assert response.status_code == 422
    assert runner.messages == []


@pytest.mark.parametrize("token", [None, "invalid-token"])
def test_agent_endpoint_requires_valid_authentication(
    test_app: FastAPI,
    runner: FakeAgentRunner,
    token: str | None,
) -> None:
    response = asyncio.run(
        send_request(test_app, {"message": "Run agent"}, token)
    )

    assert response.status_code == 401
    assert runner.messages == []


def test_basic_user_is_forbidden_before_agent_execution(
    test_app: FastAPI,
    settings: Settings,
    runner: FakeAgentRunner,
) -> None:
    _, token = provision_token(settings, Role.USER)

    response = asyncio.run(
        send_request(test_app, {"message": "Run agent"}, token)
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient permissions"}
    assert runner.messages == []


@pytest.mark.parametrize(
    ("error_type", "expected_status", "expected_detail", "category"),
    [
        (
            AgentUnavailableError,
            503,
            "Agent service is unavailable",
            "unavailable",
        ),
        (AgentTimeoutError, 504, "Agent execution timed out", "timeout"),
        (AgentExecutionError, 502, "Agent execution failed", "execution_failure"),
        (RuntimeError, 502, "Agent execution failed", "execution_failure"),
    ],
)
def test_agent_failures_are_normalized_and_audited(
    settings: Settings,
    error_type: type[Exception],
    expected_status: int,
    expected_detail: str,
    category: str,
) -> None:
    initialize_database(settings.database_path)
    application = create_app(
        settings,
        agent_runner=FailingAgentRunner(error_type),
    )
    user_id, token = provision_token(settings, Role.OFFICER)

    response = asyncio.run(
        send_request(application, {"message": "Confidential prompt"}, token)
    )

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
    records = read_agent_events(settings)
    assert len(records) == 1
    assert records[0].event_type is AuditEventType.AGENT_EXECUTION_FAILURE
    assert records[0].user_id == user_id
    assert records[0].details == {"error_category": category}


def test_adapter_normalizes_real_agent_contract_without_raw_state() -> None:
    received: dict = {}

    def workflow(**kwargs):
        received.update(kwargs)
        return {
            "status": "success",
            "task_type": "SOP_QUERY",
            "final_answer": "  Safe answer  ",
            "citations": [
                {"source": "SOP.pdf", "page": 7, "distance": 0.15},
                {"unsupported": "ignored"},
            ],
            "steps_taken": [
                {
                    "step": 1,
                    "agent": "Supervisor",
                    "action": "Classified request",
                    "private_state": "discarded",
                }
            ],
            "execution_time_seconds": 1,
            "air_gapped": True,
            "vision_data": {"internal": "discarded"},
            "rag_data": {"internal": "discarded"},
        }

    result = LangGraphAgentAdapter(workflow=workflow).run("Check SOP")

    assert received == {"user_query": "Check SOP"}
    assert result == AgentResult(
        response="Safe answer",
        task_type="SOP_QUERY",
        citations=[AgentCitation(source="SOP.pdf", page="7", distance=0.15)],
        steps=[
            AgentStep(
                step=1,
                agent="Supervisor",
                action="Classified request",
            )
        ],
        execution_time_seconds=1.0,
        air_gapped=True,
    )


def test_adapter_rejects_unknown_task_type() -> None:
    def workflow(**kwargs):
        return {
            "status": "success",
            "task_type": "Confidential prompt copied into metadata",
            "final_answer": "answer",
        }

    with pytest.raises(AgentExecutionError, match="task type is invalid"):
        LangGraphAgentAdapter(workflow=workflow).run("Check SOP")


def test_agent_success_audit_excludes_prompt_response_and_credentials(
    settings: Settings,
) -> None:
    prompt = "confidential industrial prompt value"
    model_output = "confidential model response value"
    runner = FakeAgentRunner(successful_result(response=model_output))
    initialize_database(settings.database_path)
    application = create_app(settings, agent_runner=runner)
    user_id, token = provision_token(settings, Role.ADMIN)

    response = asyncio.run(
        send_request(application, {"message": prompt}, token)
    )

    assert response.status_code == 200
    records = read_agent_events(settings)
    assert len(records) == 1
    assert records[0].event_type is AuditEventType.AGENT_EXECUTION_SUCCESS
    assert records[0].user_id == user_id
    assert records[0].details == {"task_type": "DIRECT_CHAT"}

    with connect_database(settings.database_path) as connection:
        rows = connection.execute("SELECT * FROM audit_events").fetchall()
    stored_audit = json.dumps([dict(row) for row in rows], sort_keys=True)
    for sensitive_value in (
        prompt,
        model_output,
        token,
        f"Bearer {token}",
        TEST_JWT_SECRET,
        "unused-password-hash",
    ):
        assert sensitive_value not in stored_audit


def test_phase_4_audit_events_survive_event_constraint_upgrade(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "phase-4.db"
    created_at = datetime.now(timezone.utc)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                event_type TEXT NOT NULL CHECK (event_type IN (
                    'AUTH_REGISTER_SUCCESS',
                    'AUTH_LOGIN_SUCCESS',
                    'AUTH_LOGIN_FAILURE',
                    'AUTHORIZATION_DENIED'
                )),
                user_id INTEGER,
                username TEXT,
                success INTEGER NOT NULL CHECK (success IN (0, 1)),
                resource TEXT NOT NULL,
                action TEXT NOT NULL,
                ip_address TEXT,
                details TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        connection.execute(
            """
            INSERT INTO audit_events (
                created_at, event_type, success, resource, action, details
            ) VALUES (?, 'AUTH_LOGIN_SUCCESS', 1, '/login', 'POST', '{}')
            """,
            (created_at.isoformat(),),
        )

    initialize_database(database_path)

    with connect_database(database_path) as connection:
        insert_audit_record(
            connection,
            created_at=created_at,
            event_type=AuditEventType.AGENT_EXECUTION_SUCCESS,
            user_id=1,
            username="engineer",
            success=True,
            resource="/api/v1/agent/run",
            action="POST",
            ip_address=None,
            details={"task_type": "DIRECT_CHAT"},
        )
        records = list_audit_records(connection, limit=10, offset=0)

    assert {record.event_type for record in records} == {
        AuditEventType.AUTH_LOGIN_SUCCESS,
        AuditEventType.AGENT_EXECUTION_SUCCESS,
    }
