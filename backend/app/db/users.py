"""User persistence operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import sqlite3

from app.core.roles import Role


@dataclass(frozen=True)
class User:
    """Internal persisted user record, including its password hash."""

    id: int
    username: str
    password_hash: str
    is_active: bool
    role: Role
    created_at: datetime
    updated_at: datetime


class DuplicateUsernameError(ValueError):
    """Raised when a username already exists."""


class InvalidRoleError(ValueError):
    """Raised when an unsupported role is provided."""


def create_user(
    connection: sqlite3.Connection,
    username: str,
    password_hash: str,
    role: Role | str = Role.USER,
) -> User:
    """Persist and return a new active user."""

    validated_role = _validate_role(role)
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        cursor = connection.execute(
            """
            INSERT INTO users (
                username, password_hash, is_active, role, created_at, updated_at
            ) VALUES (?, ?, 1, ?, ?, ?)
            """,
            (
                username,
                password_hash,
                validated_role.value,
                timestamp,
                timestamp,
            ),
        )
        connection.commit()
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        raise DuplicateUsernameError("Username already exists") from exc

    user = get_user_by_id(connection, cursor.lastrowid)
    if user is None:
        raise RuntimeError("Created user could not be loaded")
    return user


def get_user_by_username(
    connection: sqlite3.Connection,
    username: str,
) -> User | None:
    row = connection.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    return _to_user(row)


def get_user_by_id(
    connection: sqlite3.Connection,
    user_id: int,
) -> User | None:
    row = connection.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    return _to_user(row)


def update_password_hash(
    connection: sqlite3.Connection,
    user_id: int,
    password_hash: str,
) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    connection.execute(
        "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
        (password_hash, timestamp, user_id),
    )
    connection.commit()


def set_user_active(
    connection: sqlite3.Connection,
    user_id: int,
    is_active: bool,
) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    connection.execute(
        "UPDATE users SET is_active = ?, updated_at = ? WHERE id = ?",
        (int(is_active), timestamp, user_id),
    )
    connection.commit()


def set_user_role(
    connection: sqlite3.Connection,
    user_id: int,
    role: Role | str,
) -> None:
    """Assign a validated role through trusted application code."""

    validated_role = _validate_role(role)
    timestamp = datetime.now(timezone.utc).isoformat()
    connection.execute(
        "UPDATE users SET role = ?, updated_at = ? WHERE id = ?",
        (validated_role.value, timestamp, user_id),
    )
    connection.commit()


def _to_user(row: sqlite3.Row | None) -> User | None:
    if row is None:
        return None
    return User(
        id=row["id"],
        username=row["username"],
        password_hash=row["password_hash"],
        is_active=bool(row["is_active"]),
        role=Role(row["role"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def _validate_role(role: Role | str) -> Role:
    try:
        return Role(role)
    except ValueError as exc:
        raise InvalidRoleError(f"Unsupported role: {role}") from exc
