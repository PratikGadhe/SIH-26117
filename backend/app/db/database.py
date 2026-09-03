"""SQLite connection and initialization helpers."""

from __future__ import annotations

from collections.abc import Iterator
import sqlite3
from pathlib import Path

from fastapi import Request

from app.core.audit import AuditEventType
from app.core.roles import Role


ROLE_VALUES_SQL = ", ".join(f"'{role.value}'" for role in Role)
AUDIT_EVENT_VALUES_SQL = ", ".join(
    f"'{event_type.value}'" for event_type in AuditEventType
)


def connect_database(database_path: Path) -> sqlite3.Connection:
    """Open a configured SQLite database connection."""

    connection = sqlite3.connect(database_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(database_path: Path) -> None:
    """Create or safely update the current database schema."""

    database_path.parent.mkdir(parents=True, exist_ok=True)
    with connect_database(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
                    CHECK (is_active IN (0, 1)),
                role TEXT NOT NULL DEFAULT 'user'
                    CHECK (role IN ({ROLE_VALUES_SQL})),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """.format(ROLE_VALUES_SQL=ROLE_VALUES_SQL)
        )
        _add_role_column_to_phase_2_database(connection)
        _create_audit_schema(connection)


def _add_role_column_to_phase_2_database(
    connection: sqlite3.Connection,
) -> None:
    columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(users)").fetchall()
    }
    if "role" in columns:
        return

    connection.execute(
        """
        ALTER TABLE users
        ADD COLUMN role TEXT NOT NULL DEFAULT 'user'
            CHECK (role IN ({ROLE_VALUES_SQL}))
        """.format(ROLE_VALUES_SQL=ROLE_VALUES_SQL)
    )


def _create_audit_schema(connection: sqlite3.Connection) -> None:
    _create_audit_table(connection)
    _upgrade_audit_event_constraint(connection)
    _create_audit_indexes(connection)


def _create_audit_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            event_type TEXT NOT NULL
                CHECK (event_type IN ({AUDIT_EVENT_VALUES_SQL})),
            user_id INTEGER,
            username TEXT,
            success INTEGER NOT NULL CHECK (success IN (0, 1)),
            resource TEXT NOT NULL,
            action TEXT NOT NULL,
            ip_address TEXT,
            details TEXT NOT NULL DEFAULT '{{}}'
        )
        """.format(AUDIT_EVENT_VALUES_SQL=AUDIT_EVENT_VALUES_SQL)
    )


def _upgrade_audit_event_constraint(connection: sqlite3.Connection) -> None:
    table = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
        ("audit_events",),
    ).fetchone()
    table_sql = table["sql"] if table is not None else ""
    if all(event_type.value in table_sql for event_type in AuditEventType):
        return

    connection.execute(
        "ALTER TABLE audit_events RENAME TO audit_events_previous"
    )
    _create_audit_table(connection)
    connection.execute(
        """
        INSERT INTO audit_events (
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
        )
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
        FROM audit_events_previous
        """
    )
    connection.execute("DROP TABLE audit_events_previous")


def _create_audit_indexes(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_audit_events_created_at
        ON audit_events (created_at DESC, id DESC)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_audit_events_type
        ON audit_events (event_type)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_audit_events_user_id
        ON audit_events (user_id)
        """
    )


def get_database(request: Request) -> Iterator[sqlite3.Connection]:
    """Provide one SQLite connection for the duration of a request."""

    connection = connect_database(request.app.state.settings.database_path)
    try:
        yield connection
    finally:
        connection.close()
