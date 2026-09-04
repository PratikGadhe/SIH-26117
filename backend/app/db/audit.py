"""SQLite persistence operations for audit records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import sqlite3
from typing import Any

from app.core.audit import AuditEventType

AuditDetails = dict[str, str | list[str]]


@dataclass(frozen=True)
class AuditRecord:
    """A structured, security-safe audit record."""

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


def insert_audit_record(
    connection: sqlite3.Connection,
    *,
    created_at: datetime,
    event_type: AuditEventType,
    user_id: int | None,
    username: str | None,
    success: bool,
    resource: str,
    action: str,
    ip_address: str | None,
    details: AuditDetails,
) -> None:
    """Persist one controlled audit event."""

    connection.execute(
        """
        INSERT INTO audit_events (
            created_at,
            event_type,
            user_id,
            username,
            success,
            resource,
            action,
            ip_address,
            details
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            created_at.isoformat(),
            event_type.value,
            user_id,
            username,
            int(success),
            resource,
            action,
            ip_address,
            json.dumps(details, separators=(",", ":"), sort_keys=True),
        ),
    )
    connection.commit()


def list_audit_records(
    connection: sqlite3.Connection,
    *,
    limit: int,
    offset: int,
    event_type: AuditEventType | None = None,
    user_id: int | None = None,
) -> list[AuditRecord]:
    """Return filtered audit records in deterministic newest-first order."""

    conditions: list[str] = []
    parameters: list[Any] = []
    if event_type is not None:
        conditions.append("event_type = ?")
        parameters.append(event_type.value)
    if user_id is not None:
        conditions.append("user_id = ?")
        parameters.append(user_id)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    parameters.extend((limit, offset))
    rows = connection.execute(
        f"""
        SELECT
            id,
            created_at,
            event_type,
            user_id,
            username,
            success,
            resource,
            action,
            ip_address,
            details
        FROM audit_events
        {where_clause}
        ORDER BY created_at DESC, id DESC
        LIMIT ? OFFSET ?
        """,
        parameters,
    ).fetchall()
    return [_to_audit_record(row) for row in rows]


def _to_audit_record(row: sqlite3.Row) -> AuditRecord:
    return AuditRecord(
        id=row["id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        event_type=AuditEventType(row["event_type"]),
        user_id=row["user_id"],
        username=row["username"],
        success=bool(row["success"]),
        resource=row["resource"],
        action=row["action"],
        ip_address=row["ip_address"],
        details=json.loads(row["details"]),
    )
