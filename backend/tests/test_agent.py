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
        status="success",
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
        self.calls: list[tuple[str, str | None, str | None]] = []

    def run(
        self,
        user_query: str,
        image_path: str | None = None,
        pdf_path: str | None = None,
    ) -> AgentResult:
        self.calls.append((user_query, image_path, pdf_path))
        return self.result


class FailingAgentRunner:
    def __init__(self, error_type: type[Exception]) -> None:
        self.error_type = error_type

    def run(
        self,
        user_query: str,
        image_path: str | None = None,
        pdf_path: str | None = None,
    ) -> AgentResult:
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
        send_request(test_app, {"user_query": "Inspect the process"}, token)
    )

    assert response.status_code == 200
    assert runner.calls == [("Inspect the process", None, None)]
    assert response.json() == {
        "status": "success",
        "response": "Normalized answer",
        "task_type": "DIRECT_CHAT",
        "citations": [{"source": "manual.pdf", "page": "4", "distance": 0.2}],
        "steps": [{"step": 1, "agent": "Supervisor Agent", "action": "Classified"}],
        "execution_time_seconds": 0.25,
        "air_gapped": True,
    }


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"user_query": "   "},
        {"user_query": "valid", "unsupported": "field"},
        {"user_query": "x" * 10_001},
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
    assert runner.calls == []


@pytest.mark.parametrize("token", [None, "invalid-token"])
def test_agent_endpoint_requires_valid_authentication(
    test_app: FastAPI,
    runner: FakeAgentRunner,
    token: str | None,
) -> None:
    response = asyncio.run(send_request(test_app, {"user_query": "Run agent"}, token))

    assert response.status_code == 401
    assert runner.calls == []


def test_basic_user_is_forbidden_before_agent_execution(
    test_app: FastAPI,
    settings: Settings,
    runner: FakeAgentRunner,
) -> None:
    _, token = provision_token(settings, Role.USER)

    response = asyncio.run(send_request(test_app, {"user_query": "Run agent"}, token))

    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient permissions"}
    assert runner.calls == []


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
        send_request(
            application,
            {"user_query": "Confidential prompt"},
            token,
        )
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

    result = LangGraphAgentAdapter(workflow=workflow).run(
        "Check SOP",
        image_path="diagram.png",
        pdf_path="manual.pdf",
    )

    assert received == {
        "user_query": "Check SOP",
        "image_path": "diagram.png",
        "pdf_path": "manual.pdf",
    }
    assert result == AgentResult(
        status="success",
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


def test_adapter_rejects_known_model_failure_sentinel() -> None:
    def workflow(**kwargs):
        return {
            "status": "success",
            "task_type": "DIRECT_CHAT",
            "final_answer": "Report generation failed.",
        }

    with pytest.raises(AgentUnavailableError):
        LangGraphAgentAdapter(workflow=workflow).run("Check status")


def test_agent_success_audit_excludes_prompt_response_and_credentials(
    settings: Settings,
) -> None:
    prompt = "confidential industrial prompt value"
    model_output = "confidential model response value"
    runner = FakeAgentRunner(successful_result(response=model_output))
    initialize_database(settings.database_path)
    application = create_app(settings, agent_runner=runner)
    user_id, token = provision_token(settings, Role.ADMIN)

    response = asyncio.run(send_request(application, {"user_query": prompt}, token))

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


VALID_PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
VALID_JPEG_BYTES = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb"
)
VALID_PDF_BYTES = b"%PDF-1.5\n%test PDF header content\n%%EOF"


async def send_multipart_request(
    application: FastAPI,
    data: dict[str, str],
    files: dict[str, tuple[str, bytes, str]] | None,
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
            data=data,
            files=files,
            headers=headers,
        )


def test_valid_png_upload_passes_temporary_file_and_cleans_up(
    test_app: FastAPI,
    settings: Settings,
    runner: FakeAgentRunner,
) -> None:
    _, token = provision_token(settings, Role.WORKER)

    response = asyncio.run(
        send_multipart_request(
            test_app,
            {"user_query": "Inspect pump schematic"},
            {"file": ("schematic.png", VALID_PNG_BYTES, "image/png")},
            token,
        )
    )

    assert response.status_code == 200
    assert len(runner.calls) == 1
    query, image_path, pdf_path = runner.calls[0]
    assert query == "Inspect pump schematic"
    assert image_path is not None
    assert image_path.endswith(".png")
    assert pdf_path is None
    # Verify temporary file was deleted after request execution
    assert not Path(image_path).exists()


def test_valid_jpeg_upload_accepted(
    test_app: FastAPI,
    settings: Settings,
    runner: FakeAgentRunner,
) -> None:
    _, token = provision_token(settings, Role.WORKER)

    response = asyncio.run(
        send_multipart_request(
            test_app,
            {"user_query": "Inspect valve photo"},
            {"file": ("valve.jpg", VALID_JPEG_BYTES, "image/jpeg")},
            token,
        )
    )

    assert response.status_code == 200
    assert len(runner.calls) == 1
    assert runner.calls[0][1] is not None
    assert runner.calls[0][1].endswith(".jpg")
    assert not Path(runner.calls[0][1]).exists()


def test_unsupported_file_extension_rejected_with_415(
    test_app: FastAPI,
    settings: Settings,
    runner: FakeAgentRunner,
) -> None:
    _, token = provision_token(settings, Role.WORKER)

    response = asyncio.run(
        send_multipart_request(
            test_app,
            {"user_query": "Inspect document"},
            {"file": ("notes.txt", b"plain text content", "text/plain")},
            token,
        )
    )

    assert response.status_code == 415
    assert "Unsupported file format" in response.json()["detail"]
    assert runner.calls == []


def test_spoofed_extension_magic_bytes_rejected_with_415(
    test_app: FastAPI,
    settings: Settings,
    runner: FakeAgentRunner,
) -> None:
    _, token = provision_token(settings, Role.WORKER)

    response = asyncio.run(
        send_multipart_request(
            test_app,
            {"user_query": "Inspect image"},
            {"file": ("exploit.png", b"NOT_A_PNG_FILE", "image/png")},
            token,
        )
    )

    assert response.status_code == 415
    assert "does not match" in response.json()["detail"]
    assert runner.calls == []


def test_empty_image_file_rejected_with_400(
    test_app: FastAPI,
    settings: Settings,
    runner: FakeAgentRunner,
) -> None:
    _, token = provision_token(settings, Role.WORKER)

    response = asyncio.run(
        send_multipart_request(
            test_app,
            {"user_query": "Inspect image"},
            {"file": ("empty.png", b"", "image/png")},
            token,
        )
    )

    assert response.status_code == 400
    assert "empty" in response.json()["detail"]
    assert runner.calls == []


def test_oversized_image_rejected_with_413(
    test_app: FastAPI,
    settings: Settings,
    runner: FakeAgentRunner,
) -> None:
    _, token = provision_token(settings, Role.WORKER)

    oversized_data = VALID_PNG_BYTES + (b"0" * (10 * 1024 * 1024 + 1))
    response = asyncio.run(
        send_multipart_request(
            test_app,
            {"user_query": "Inspect image"},
            {"file": ("huge.png", oversized_data, "image/png")},
            token,
        )
    )

    assert response.status_code == 413
    assert "exceeds" in response.json()["detail"]
    assert runner.calls == []


def test_temporary_file_cleaned_up_on_agent_failure(
    settings: Settings,
) -> None:
    initialize_database(settings.database_path)
    _, token = provision_token(settings, Role.WORKER)
    captured_paths = []

    class CapturingFailingRunner:
        def run(
            self,
            user_query: str,
            image_path: str | None = None,
            pdf_path: str | None = None,
        ) -> AgentResult:
            captured_paths.append(image_path)
            raise AgentExecutionError("Internal model execution failure")

    application = create_app(settings, agent_runner=CapturingFailingRunner())

    response = asyncio.run(
        send_multipart_request(
            application,
            {"user_query": "Inspect diagram"},
            {"file": ("diagram.png", VALID_PNG_BYTES, "image/png")},
            token,
        )
    )

    assert response.status_code == 502
    assert len(captured_paths) == 1
    assert captured_paths[0] is not None
    assert not Path(captured_paths[0]).exists()


def test_unauthenticated_multipart_request_rejected_with_401(
    test_app: FastAPI,
) -> None:
    response = asyncio.run(
        send_multipart_request(
            test_app,
            {"user_query": "Inspect image"},
            {"file": ("diagram.png", VALID_PNG_BYTES, "image/png")},
            token=None,
        )
    )

    assert response.status_code == 401


def test_unauthorized_user_role_multipart_rejected_with_403(
    test_app: FastAPI,
    settings: Settings,
) -> None:
    _, token = provision_token(settings, Role.USER)

    response = asyncio.run(
        send_multipart_request(
            test_app,
            {"user_query": "Inspect image"},
            {"file": ("diagram.png", VALID_PNG_BYTES, "image/png")},
            token=token,
        )
    )

    assert response.status_code == 403


def test_multipart_without_file_executes_as_text_only(
    test_app: FastAPI,
    settings: Settings,
    runner: FakeAgentRunner,
) -> None:
    _, token = provision_token(settings, Role.WORKER)

    response = asyncio.run(
        send_multipart_request(
            test_app,
            {"user_query": "Form text only query"},
            files=None,
            token=token,
        )
    )

    assert response.status_code == 200
    assert runner.calls == [("Form text only query", None, None)]


def test_valid_pdf_upload_executes_pdf_workflow(
    test_app: FastAPI,
    settings: Settings,
    runner: FakeAgentRunner,
) -> None:
    _, token = provision_token(settings, Role.WORKER)

    response = asyncio.run(
        send_multipart_request(
            test_app,
            {"user_query": "Analyze inspection report"},
            {"file": ("report.pdf", VALID_PDF_BYTES, "application/pdf")},
            token,
        )
    )

    assert response.status_code == 200
    assert len(runner.calls) == 1
    query, image_path, pdf_path = runner.calls[0]
    assert query == "Analyze inspection report"
    assert image_path is None
    assert pdf_path is not None
    assert pdf_path.endswith(".pdf")
    assert not Path(pdf_path).exists()


def test_spoofed_pdf_magic_bytes_rejected_with_415(
    test_app: FastAPI,
    settings: Settings,
    runner: FakeAgentRunner,
) -> None:
    _, token = provision_token(settings, Role.WORKER)

    response = asyncio.run(
        send_multipart_request(
            test_app,
            {"user_query": "Analyze document"},
            {"file": ("malicious.pdf", b"NOT_A_VALID_PDF_HEADER", "application/pdf")},
            token,
        )
    )

    assert response.status_code == 415
    assert "does not match" in response.json()["detail"]
    assert runner.calls == []


def test_empty_pdf_file_rejected_with_400(
    test_app: FastAPI,
    settings: Settings,
    runner: FakeAgentRunner,
) -> None:
    _, token = provision_token(settings, Role.WORKER)

    response = asyncio.run(
        send_multipart_request(
            test_app,
            {"user_query": "Analyze document"},
            {"file": ("empty.pdf", b"", "application/pdf")},
            token,
        )
    )

    assert response.status_code == 400
    assert "empty" in response.json()["detail"]
    assert runner.calls == []


def test_oversized_pdf_rejected_with_413(
    test_app: FastAPI,
    settings: Settings,
    runner: FakeAgentRunner,
) -> None:
    _, token = provision_token(settings, Role.WORKER)

    oversized_data = VALID_PDF_BYTES + (b"0" * (10 * 1024 * 1024 + 1))
    response = asyncio.run(
        send_multipart_request(
            test_app,
            {"user_query": "Analyze document"},
            {"file": ("huge.pdf", oversized_data, "application/pdf")},
            token,
        )
    )

    assert response.status_code == 413
    assert "exceeds" in response.json()["detail"]
    assert runner.calls == []


def test_temporary_pdf_cleaned_up_on_agent_failure(
    settings: Settings,
) -> None:
    initialize_database(settings.database_path)
    _, token = provision_token(settings, Role.WORKER)
    captured_paths = []

    class CapturingFailingRunner:
        def run(
            self,
            user_query: str,
            image_path: str | None = None,
            pdf_path: str | None = None,
        ) -> AgentResult:
            captured_paths.append(pdf_path)
            raise AgentExecutionError("Internal model execution failure")

    application = create_app(settings, agent_runner=CapturingFailingRunner())

    response = asyncio.run(
        send_multipart_request(
            application,
            {"user_query": "Analyze document"},
            {"file": ("report.pdf", VALID_PDF_BYTES, "application/pdf")},
            token,
        )
    )

    assert response.status_code == 502
    assert len(captured_paths) == 1
    assert captured_paths[0] is not None
    assert not Path(captured_paths[0]).exists()
