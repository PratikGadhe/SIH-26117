"""Safe application-level security audit service."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import sqlite3

from app.core.audit import AuditEventType
from app.core.roles import Role
from app.db.audit import AuditDetails, insert_audit_record

logger = logging.getLogger(__name__)


def record_registration_success(
    connection: sqlite3.Connection,
    *,
    user_id: int,
    username: str,
    resource: str,
    action: str,
    ip_address: str | None,
) -> None:
    _record_event(
        connection,
        event_type=AuditEventType.AUTH_REGISTER_SUCCESS,
        user_id=user_id,
        username=username,
        success=True,
        resource=resource,
        action=action,
        ip_address=ip_address,
        details={},
    )


def record_login_success(
    connection: sqlite3.Connection,
    *,
    user_id: int,
    username: str,
    resource: str,
    action: str,
    ip_address: str | None,
) -> None:
    _record_event(
        connection,
        event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
        user_id=user_id,
        username=username,
        success=True,
        resource=resource,
        action=action,
        ip_address=ip_address,
        details={},
    )


def record_login_failure(
    connection: sqlite3.Connection,
    *,
    username: str,
    resource: str,
    action: str,
    ip_address: str | None,
) -> None:
    _record_event(
        connection,
        event_type=AuditEventType.AUTH_LOGIN_FAILURE,
        user_id=None,
        username=username,
        success=False,
        resource=resource,
        action=action,
        ip_address=ip_address,
        details={"reason": "invalid_credentials"},
    )


def record_authorization_denied(
    connection: sqlite3.Connection,
    *,
    user_id: int,
    username: str,
    role: Role,
    required_roles: frozenset[Role],
    resource: str,
    action: str,
    ip_address: str | None,
) -> None:
    _record_event(
        connection,
        event_type=AuditEventType.AUTHORIZATION_DENIED,
        user_id=user_id,
        username=username,
        success=False,
        resource=resource,
        action=action,
        ip_address=ip_address,
        details={
            "role": role.value,
            "required_roles": sorted(item.value for item in required_roles),
        },
    )


def _record_event(
    connection: sqlite3.Connection,
    *,
    event_type: AuditEventType,
    user_id: int | None,
    username: str | None,
    success: bool,
    resource: str,
    action: str,
    ip_address: str | None,
    details: AuditDetails,
) -> None:
    try:
        insert_audit_record(
            connection,
            created_at=datetime.now(timezone.utc),
            event_type=event_type,
            user_id=user_id,
            username=username,
            success=success,
            resource=resource,
            action=action,
            ip_address=ip_address,
            details=details,
        )
    except sqlite3.Error:
        connection.rollback()
        logger.warning(
            "Security audit event could not be persisted: %s",
            event_type.value,
        )
