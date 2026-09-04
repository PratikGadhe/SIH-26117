"""Environment-based application configuration."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

BACKEND_DIRECTORY = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = BACKEND_DIRECTORY / "data" / "cognivault.db"
SUPPORTED_JWT_ALGORITHMS = {"HS256", "HS384", "HS512"}


@dataclass(frozen=True)
class Settings:
    """Runtime settings needed by the Phase 2 backend."""

    database_path: Path = DEFAULT_DATABASE_PATH
    jwt_secret: str | None = None
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 30

    def __post_init__(self) -> None:
        if self.jwt_algorithm not in SUPPORTED_JWT_ALGORITHMS:
            raise ValueError("JWT algorithm must be an HMAC SHA-2 algorithm")
        if self.jwt_expiration_minutes <= 0:
            raise ValueError("JWT expiration must be greater than zero")

    @classmethod
    def from_environment(cls) -> Settings:
        """Load settings without reading or creating a secrets file."""

        database_value = os.getenv("COGNIVAULT_DATABASE_PATH")
        expiration_value = os.getenv("COGNIVAULT_JWT_EXPIRATION_MINUTES", "30")

        try:
            expiration_minutes = int(expiration_value)
        except ValueError as exc:
            raise ValueError(
                "COGNIVAULT_JWT_EXPIRATION_MINUTES must be an integer"
            ) from exc

        return cls(
            database_path=(
                Path(database_value).expanduser()
                if database_value
                else DEFAULT_DATABASE_PATH
            ),
            jwt_secret=os.getenv("COGNIVAULT_JWT_SECRET"),
            jwt_algorithm=os.getenv("COGNIVAULT_JWT_ALGORITHM", "HS256"),
            jwt_expiration_minutes=expiration_minutes,
        )
