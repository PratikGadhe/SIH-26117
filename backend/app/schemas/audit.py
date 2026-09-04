"""Audit retrieval API schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.audit import AuditEventType
from app.db.audit import AuditDetails


class AuditRecordResponse(BaseModel):
    """Safe structured representation of one security audit record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    event_type: AuditEventType
    user_id: int | None
    username: str | None
    success: bool
    resource: str
    action: str
    ip_address: str | None
    details: AuditDetails
