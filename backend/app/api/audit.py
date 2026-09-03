"""Administrator-only security audit retrieval."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import DatabaseConnection, require_roles
from app.core.audit import AuditEventType
from app.core.roles import Role
from app.db.audit import list_audit_records
from app.db.users import User
from app.schemas.audit import AuditRecordResponse

router = APIRouter(prefix="/audit", tags=["audit"])
AdminUser = Annotated[User, Depends(require_roles(Role.ADMIN))]


@router.get("", response_model=list[AuditRecordResponse])
def audit_records(
    _: AdminUser,
    connection: DatabaseConnection,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    event_type: AuditEventType | None = None,
    user_id: Annotated[int | None, Query(gt=0)] = None,
) -> list[AuditRecordResponse]:
    """Return filtered security events, newest first."""

    records = list_audit_records(
        connection,
        limit=limit,
        offset=offset,
        event_type=event_type,
        user_id=user_id,
    )
    return [AuditRecordResponse.model_validate(record) for record in records]
