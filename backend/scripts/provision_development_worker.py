"""Explicit local command for provisioning a development worker account."""

from __future__ import annotations

import argparse
from getpass import getpass
import os
from pathlib import Path
import sys

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from app.core.config import Settings
from app.core.roles import Role
from app.core.security import hash_password
from app.db.database import connect_database, initialize_database
from app.db.users import DuplicateUsernameError, User, create_user
from app.services.audit import record_registration_success

ENABLE_VALUE = "1"
ENABLE_VARIABLE = "COGNIVAULT_ENABLE_DEV_PROVISIONING"
PASSWORD_VARIABLE = "COGNIVAULT_DEV_PASSWORD"


class DevelopmentAccountInputError(ValueError):
    """Raised when local provisioning input is unsafe or invalid."""


def provision_development_worker(
    database_path: Path,
    username: str,
    password: str,
) -> User:
    """Create one worker without weakening the public registration policy."""

    normalized_username = username.strip()
    if not normalized_username or len(normalized_username) > 64:
        raise DevelopmentAccountInputError(
            "Username must contain between 1 and 64 non-blank characters."
        )
    if len(password) < 8 or len(password) > 256:
        raise DevelopmentAccountInputError(
            "Password must contain between 8 and 256 characters."
        )

    initialize_database(database_path)
    connection = connect_database(database_path)
    try:
        user = create_user(
            connection,
            normalized_username,
            hash_password(password),
            Role.WORKER,
        )
        record_registration_success(
            connection,
            user_id=user.id,
            username=user.username,
            resource="local-development-provisioning",
            action="CREATE_WORKER",
            ip_address=None,
        )
        return user
    finally:
        connection.close()


def _read_password() -> str:
    configured_password = os.getenv(PASSWORD_VARIABLE)
    if configured_password is not None:
        return configured_password

    password = getpass("Development worker password: ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        raise DevelopmentAccountInputError("Passwords do not match.")
    return password


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a local worker account for Cognivault development."
    )
    parser.add_argument("--username", required=True)
    arguments = parser.parse_args()

    if os.getenv(ENABLE_VARIABLE) != ENABLE_VALUE:
        parser.error(
            f"Set {ENABLE_VARIABLE}={ENABLE_VALUE} to acknowledge "
            "development-only provisioning."
        )

    try:
        user = provision_development_worker(
            Settings.from_environment().database_path,
            arguments.username,
            _read_password(),
        )
    except DuplicateUsernameError:
        parser.error("That username already exists; choose another username.")
    except DevelopmentAccountInputError as exc:
        parser.error(str(exc))

    print(
        f"Development account created for {user.username!r} "
        f"with role {user.role.value!r}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
