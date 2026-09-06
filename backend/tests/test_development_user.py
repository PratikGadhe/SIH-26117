from pathlib import Path
import os
import secrets
import subprocess
import sys

import pytest

from app.core.roles import Role
from app.core.security import verify_password
from app.db.audit import list_audit_records
from app.db.database import connect_database
from app.db.users import DuplicateUsernameError, get_user_by_username

SCRIPTS_DIRECTORY = Path(__file__).resolve().parents[1] / "scripts"
SCRIPT_PATH = SCRIPTS_DIRECTORY / "provision_development_worker.py"
if str(SCRIPTS_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIRECTORY))

from provision_development_worker import DevelopmentAccountInputError
from provision_development_worker import provision_development_worker


def test_provision_development_worker_creates_audited_worker(tmp_path: Path) -> None:
    database_path = tmp_path / "development.db"
    password = secrets.token_urlsafe(24)

    created = provision_development_worker(
        database_path,
        "  local-worker  ",
        password,
    )

    with connect_database(database_path) as connection:
        stored = get_user_by_username(connection, "local-worker")
        records = list_audit_records(connection, limit=10, offset=0)

    assert created.role is Role.WORKER
    assert stored is not None
    assert stored.role is Role.WORKER
    assert verify_password(password, stored.password_hash)
    assert len(records) == 1
    assert records[0].username == "local-worker"
    assert records[0].resource == "local-development-provisioning"
    assert records[0].action == "CREATE_WORKER"
    assert password not in str(records[0])


@pytest.mark.parametrize(
    ("username", "password"),
    [
        ("   ", secrets.token_urlsafe(24)),
        ("x" * 65, secrets.token_urlsafe(24)),
        ("local-worker", "short"),
        ("local-worker", "x" * 257),
    ],
)
def test_provision_development_worker_rejects_invalid_input(
    tmp_path: Path,
    username: str,
    password: str,
) -> None:
    with pytest.raises(DevelopmentAccountInputError):
        provision_development_worker(tmp_path / "development.db", username, password)


def test_provision_development_worker_refuses_duplicate_username(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "development.db"
    first_password = secrets.token_urlsafe(24)
    second_password = secrets.token_urlsafe(24)
    provision_development_worker(database_path, "local-worker", first_password)

    with pytest.raises(DuplicateUsernameError):
        provision_development_worker(database_path, "local-worker", second_password)

    with connect_database(database_path) as connection:
        stored = get_user_by_username(connection, "local-worker")

    assert stored is not None
    assert verify_password(first_password, stored.password_hash)
    assert not verify_password(second_password, stored.password_hash)


def test_command_requires_explicit_development_opt_in(tmp_path: Path) -> None:
    environment = os.environ.copy()
    environment.pop("COGNIVAULT_ENABLE_DEV_PROVISIONING", None)
    environment["COGNIVAULT_DATABASE_PATH"] = str(tmp_path / "development.db")
    environment["COGNIVAULT_DEV_PASSWORD"] = secrets.token_urlsafe(24)

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--username", "local-worker"],
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )

    assert result.returncode == 2
    assert "COGNIVAULT_ENABLE_DEV_PROVISIONING=1" in result.stderr
    assert not (tmp_path / "development.db").exists()


def test_command_provisions_without_printing_password(tmp_path: Path) -> None:
    database_path = tmp_path / "development.db"
    password = secrets.token_urlsafe(24)
    environment = os.environ.copy()
    environment["COGNIVAULT_ENABLE_DEV_PROVISIONING"] = "1"
    environment["COGNIVAULT_DATABASE_PATH"] = str(database_path)
    environment["COGNIVAULT_DEV_PASSWORD"] = password

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--username", "local-worker"],
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )

    assert result.returncode == 0
    assert "local-worker" in result.stdout
    assert "worker" in result.stdout
    assert password not in result.stdout
    assert password not in result.stderr


def test_provision_development_worker_resets_password_when_requested(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "development.db"
    first_password = secrets.token_urlsafe(24)
    second_password = secrets.token_urlsafe(24)

    first_user = provision_development_worker(
        database_path, "local-worker", first_password
    )
    assert first_user.role is Role.WORKER

    updated_user = provision_development_worker(
        database_path, "local-worker", second_password, reset_password=True
    )
    assert updated_user.id == first_user.id
    assert updated_user.role is Role.WORKER

    with connect_database(database_path) as connection:
        stored = get_user_by_username(connection, "local-worker")
        records = list_audit_records(connection, limit=10, offset=0)

    assert stored is not None
    assert verify_password(second_password, stored.password_hash)
    assert not verify_password(first_password, stored.password_hash)
    assert len(records) == 2
    assert records[0].action == "RESET_WORKER_PASSWORD"


def test_command_resets_password_with_flag(tmp_path: Path) -> None:
    database_path = tmp_path / "development.db"
    first_password = secrets.token_urlsafe(24)
    second_password = secrets.token_urlsafe(24)

    provision_development_worker(database_path, "local-worker", first_password)

    environment = os.environ.copy()
    environment["COGNIVAULT_ENABLE_DEV_PROVISIONING"] = "1"
    environment["COGNIVAULT_DATABASE_PATH"] = str(database_path)
    environment["COGNIVAULT_DEV_PASSWORD"] = second_password

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--username",
            "local-worker",
            "--reset-password",
        ],
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )

    assert result.returncode == 0
    assert "updated" in result.stdout
    assert "local-worker" in result.stdout
    assert second_password not in result.stdout

    with connect_database(database_path) as connection:
        stored = get_user_by_username(connection, "local-worker")

    assert stored is not None
    assert verify_password(second_password, stored.password_hash)
    assert not verify_password(first_password, stored.password_hash)
