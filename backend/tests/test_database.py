import asyncio
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

import pytest

from app.core.config import Settings
from app.core.roles import Role
from app.db.database import connect_database, initialize_database
from app.db.users import DuplicateUsernameError, InvalidRoleError, create_user
from app.db.users import get_user_by_username
from app.main import create_app


def test_application_lifespan_initializes_fresh_database(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "fresh" / "cognivault.db"
    application = create_app(Settings(database_path=database_path))

    async def run_lifespan() -> None:
        async with application.router.lifespan_context(application):
            assert database_path.is_file()

    asyncio.run(run_lifespan())

    with connect_database(database_path) as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    assert {"users", "audit_events"} <= tables


def test_database_initializes_users_table(tmp_path: Path) -> None:
    database_path = tmp_path / "database" / "test.db"

    initialize_database(database_path)

    assert database_path.is_file()
    with connect_database(database_path) as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    assert {"users", "audit_events"} <= tables


def test_user_can_be_persisted(tmp_path: Path) -> None:
    database_path = tmp_path / "test.db"
    initialize_database(database_path)

    with connect_database(database_path) as connection:
        created = create_user(connection, "engineer", "stored-password-hash")
        persisted = get_user_by_username(connection, "engineer")

    assert persisted == created
    assert persisted is not None
    assert persisted.is_active is True


def test_duplicate_username_is_rejected(tmp_path: Path) -> None:
    database_path = tmp_path / "test.db"
    initialize_database(database_path)

    with connect_database(database_path) as connection:
        create_user(connection, "engineer", "first-hash")
        with pytest.raises(DuplicateUsernameError):
            create_user(connection, "ENGINEER", "second-hash")


@pytest.mark.parametrize("role", list(Role))
def test_valid_roles_are_persisted(tmp_path: Path, role: Role) -> None:
    database_path = tmp_path / f"{role.value}.db"
    initialize_database(database_path)

    with connect_database(database_path) as connection:
        user = create_user(connection, role.value, "hash", role=role)

    assert user.role is role


def test_invalid_role_is_rejected(tmp_path: Path) -> None:
    database_path = tmp_path / "test.db"
    initialize_database(database_path)

    with connect_database(database_path) as connection:
        with pytest.raises(InvalidRoleError):
            create_user(connection, "intruder", "hash", role="superadmin")


def test_phase_2_database_is_upgraded_without_losing_users(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "phase-2.db"
    timestamp = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
                    CHECK (is_active IN (0, 1)),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO users (
                username, password_hash, is_active, created_at, updated_at
            ) VALUES (?, ?, 1, ?, ?)
            """,
            ("existing-user", "existing-hash", timestamp, timestamp),
        )

    initialize_database(database_path)

    with connect_database(database_path) as connection:
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(users)").fetchall()
        }
        user = get_user_by_username(connection, "existing-user")
    assert "role" in columns
    assert user is not None
    assert user.password_hash == "existing-hash"
    assert user.role is Role.USER
