"""Authenticated API boundary for agent execution."""

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies import AgentServiceDependency, DatabaseConnection
from app.api.dependencies import get_client_ip, require_roles
from app.core.roles import Role
from app.db.users import User
from app.integrations.agent import AgentExecutionError, AgentTimeoutError
from app.integrations.agent import AgentUnavailableError
from app.schemas.agent import AgentRunRequest, AgentRunResponse
from app.services.audit import record_agent_execution_failure
from app.services.audit import record_agent_execution_success

router = APIRouter(prefix="/agent", tags=["agent integration"])
AgentUser = Annotated[
    User,
    Depends(require_roles(Role.ADMIN, Role.OFFICER, Role.WORKER)),
]


@router.post(
    "/run",
    response_model=AgentRunResponse,
    responses={
        502: {"description": "Agent execution failed"},
        503: {"description": "Agent service unavailable"},
        504: {"description": "Agent execution timed out"},
    },
)
def run_agent(
    payload: AgentRunRequest,
    request: Request,
    user: AgentUser,
    connection: DatabaseConnection,
    service: AgentServiceDependency,
) -> AgentRunResponse:
    """Execute one stateless request through the teammate LangGraph adapter."""

    try:
        result = service.run(payload.user_query)
    except AgentTimeoutError as exc:
        _record_failure(connection, request, user, exc.audit_category)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Agent execution timed out",
        ) from exc
    except AgentUnavailableError as exc:
        _record_failure(connection, request, user, exc.audit_category)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent service is unavailable",
        ) from exc
    except AgentExecutionError as exc:
        _record_failure(connection, request, user, exc.audit_category)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Agent execution failed",
        ) from exc

    record_agent_execution_success(
        connection,
        user_id=user.id,
        username=user.username,
        task_type=result.task_type,
        resource=request.url.path,
        action=request.method,
        ip_address=get_client_ip(request),
    )
    return AgentRunResponse.model_validate(result)


def _record_failure(
    connection: sqlite3.Connection,
    request: Request,
    user: User,
    error_category: str,
) -> None:
    record_agent_execution_failure(
        connection,
        user_id=user.id,
        username=user.username,
        error_category=error_category,
        resource=request.url.path,
        action=request.method,
        ip_address=get_client_ip(request),
    )
