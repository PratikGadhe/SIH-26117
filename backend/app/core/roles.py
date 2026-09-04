"""Role definitions for application-level authorization."""

from enum import StrEnum


class Role(StrEnum):
    """Supported Cognivault application roles."""

    ADMIN = "admin"
    OFFICER = "officer"
    WORKER = "worker"
    USER = "user"
