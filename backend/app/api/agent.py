"""Authenticated API boundary for agent execution."""

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.datastructures import UploadFile

from app.api.dependencies import AgentServiceDependency, DatabaseConnection
from app.api.dependencies import get_client_ip, require_roles
from app.core.roles import Role
from app.core.upload import secure_temporary_image, secure_temporary_upload
from app.db.users import User
from app.integrations.agent import AgentExecutionError, AgentResult, AgentTimeoutError
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
        400: {"description": "Bad request or empty file"},
        413: {"description": "Uploaded image exceeds size limit"},
        415: {"description": "Unsupported media type or format mismatch"},
        422: {"description": "Invalid input query"},
        502: {"description": "Agent execution failed"},
        503: {"description": "Agent service unavailable"},
        504: {"description": "Agent execution timed out"},
    },
)
async def run_agent(
    request: Request,
    user: AgentUser,
    connection: DatabaseConnection,
    service: AgentServiceDependency,
) -> AgentRunResponse:
    """Execute one stateless request through the teammate LangGraph adapter."""

    content_type = request.headers.get("content-type", "")
    user_query: str
    upload_file: UploadFile | None = None

    if content_type.startswith("application/json"):
        try:
            body = await request.json()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid JSON request body",
            ) from exc
        try:
            payload = AgentRunRequest.model_validate(body)
        except ValidationError as exc:
            raise RequestValidationError(exc.errors()) from exc
        user_query = payload.user_query
    elif content_type.startswith("multipart/form-data") or content_type.startswith(
        "application/x-www-form-urlencoded"
    ):
        try:
            form = await request.form()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not parse multipart form data",
            ) from exc

        raw_query = form.get("user_query")
        if not raw_query or not isinstance(raw_query, str):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Field 'user_query' is required",
            )
        try:
            payload = AgentRunRequest(user_query=raw_query)
        except ValidationError as exc:
            raise RequestValidationError(exc.errors()) from exc
        user_query = payload.user_query

        form_file = form.get("file")
        if isinstance(form_file, UploadFile) and form_file.filename:
            upload_file = form_file
    else:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported Content-Type. Use application/json or multipart/form-data.",
        )

    if upload_file is not None:
        with secure_temporary_upload(upload_file) as (temp_path, file_kind):
            image_path = temp_path if file_kind == "image" else None
            pdf_path = temp_path if file_kind == "pdf" else None
            result = _execute_service(
                service=service,
                connection=connection,
                request=request,
                user=user,
                user_query=user_query,
                image_path=image_path,
                pdf_path=pdf_path,
            )
    else:
        result = _execute_service(
            service=service,
            connection=connection,
            request=request,
            user=user,
            user_query=user_query,
            image_path=None,
            pdf_path=None,
        )

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


def _execute_service(
    service: AgentServiceDependency,
    connection: sqlite3.Connection,
    request: Request,
    user: User,
    user_query: str,
    image_path: str | None = None,
    pdf_path: str | None = None,
) -> AgentResult:
    try:
        return service.run(user_query, image_path=image_path, pdf_path=pdf_path)
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
