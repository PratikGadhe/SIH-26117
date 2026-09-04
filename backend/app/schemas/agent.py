"""Stable request and response schemas for agent execution."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgentRunRequest(BaseModel):
    """One stateless text request for the existing agent workflow."""

    model_config = ConfigDict(extra="forbid")

    user_query: str = Field(min_length=1, max_length=10_000)

    @field_validator("user_query")
    @classmethod
    def user_query_must_not_be_blank(cls, value: str) -> str:
        user_query = value.strip()
        if not user_query:
            raise ValueError("User query must not be blank")
        return user_query


class AgentCitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: str
    page: str
    distance: float | None = None


class AgentStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    step: int
    agent: str
    action: str


class AgentRunResponse(BaseModel):
    """Normalized agent output without exposing raw LangGraph state."""

    model_config = ConfigDict(from_attributes=True)

    status: Literal["success"]
    response: str
    task_type: str
    citations: list[AgentCitationResponse]
    steps: list[AgentStepResponse]
    execution_time_seconds: float = Field(ge=0)
    air_gapped: bool
