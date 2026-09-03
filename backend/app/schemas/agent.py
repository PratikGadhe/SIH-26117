"""Stable request and response schemas for agent execution."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgentRunRequest(BaseModel):
    """One stateless text request for the existing agent workflow."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=10_000)

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        message = value.strip()
        if not message:
            raise ValueError("Message must not be blank")
        return message


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

    response: str
    task_type: str
    citations: list[AgentCitationResponse]
    steps: list[AgentStepResponse]
    execution_time_seconds: float = Field(ge=0)
    air_gapped: bool
