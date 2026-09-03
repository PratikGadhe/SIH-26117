"""Controlled event types for application-level security auditing."""

from enum import StrEnum


class AuditEventType(StrEnum):
    """Security events currently emitted by Cognivault."""

    AUTH_REGISTER_SUCCESS = "AUTH_REGISTER_SUCCESS"
    AUTH_LOGIN_SUCCESS = "AUTH_LOGIN_SUCCESS"
    AUTH_LOGIN_FAILURE = "AUTH_LOGIN_FAILURE"
    AUTHORIZATION_DENIED = "AUTHORIZATION_DENIED"
    AGENT_EXECUTION_SUCCESS = "AGENT_EXECUTION_SUCCESS"
    AGENT_EXECUTION_FAILURE = "AGENT_EXECUTION_FAILURE"
