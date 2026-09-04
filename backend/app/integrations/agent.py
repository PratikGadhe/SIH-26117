"""Thin adapter for the teammate-owned LangGraph agent service."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any, Literal, Protocol

WorkflowCallable = Callable[..., dict[str, Any]]
AGENT_TASK_TYPES = frozenset(
    {"DIRECT_CHAT", "HYBRID_AUDIT", "SOP_QUERY", "VISION_INSPECTION"}
)


class AgentIntegrationError(RuntimeError):
    """Base class for normalized agent-subsystem failures."""

    audit_category = "execution_failure"


class AgentUnavailableError(AgentIntegrationError):
    """Raised when agent dependencies or the local model are unavailable."""

    audit_category = "unavailable"


class AgentTimeoutError(AgentIntegrationError):
    """Raised when the teammate agent reports an execution timeout."""

    audit_category = "timeout"


class AgentExecutionError(AgentIntegrationError):
    """Raised when execution or output normalization fails."""


@dataclass(frozen=True)
class AgentCitation:
    source: str
    page: str
    distance: float | None = None


@dataclass(frozen=True)
class AgentStep:
    step: int
    agent: str
    action: str


@dataclass(frozen=True)
class AgentResult:
    status: Literal["success"]
    response: str
    task_type: str
    citations: list[AgentCitation]
    steps: list[AgentStep]
    execution_time_seconds: float
    air_gapped: bool


class AgentRunner(Protocol):
    """Stable backend-facing contract implemented by agent adapters."""

    def run(
        self,
        user_query: str,
        image_path: str | None = None,
        pdf_path: str | None = None,
    ) -> AgentResult:
        """Execute one stateless agent request."""


class LangGraphAgentAdapter:
    """Translate between the backend contract and the existing agent service."""

    def __init__(self, workflow: WorkflowCallable | None = None) -> None:
        self._workflow = workflow

    def run(
        self,
        user_query: str,
        image_path: str | None = None,
        pdf_path: str | None = None,
    ) -> AgentResult:
        workflow = self._workflow or _load_teammate_workflow()
        try:
            raw_result = workflow(
                user_query=user_query,
                image_path=image_path,
                pdf_path=pdf_path,
            )
        except TimeoutError as exc:
            raise AgentTimeoutError("Agent execution timed out") from exc
        except AgentIntegrationError:
            raise
        except Exception as exc:
            raise AgentExecutionError("Agent execution failed") from exc

        return _normalize_result(raw_result)


@lru_cache(maxsize=1)
def _load_teammate_workflow() -> WorkflowCallable:
    agent_service_path = (
        Path(__file__).resolve().parents[3] / "agents" / "agent_service.py"
    )
    if not agent_service_path.is_file():
        raise AgentUnavailableError("Agent service entry point is unavailable")

    spec = importlib.util.spec_from_file_location(
        "cognivault_teammate_agent_service",
        agent_service_path,
    )
    if spec is None or spec.loader is None:
        raise AgentUnavailableError("Agent service cannot be loaded")

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except (ImportError, ModuleNotFoundError) as exc:
        raise AgentUnavailableError("Agent dependencies are unavailable") from exc

    return _get_workflow_callable(module)


def _get_workflow_callable(module: ModuleType) -> WorkflowCallable:
    workflow = getattr(module, "run_agentic_workflow", None)
    if not callable(workflow):
        raise AgentUnavailableError("Agent service entry point is invalid")
    return workflow


def _normalize_result(raw_result: object) -> AgentResult:
    if not isinstance(raw_result, dict):
        raise AgentExecutionError("Agent returned an invalid result")

    status = raw_result.get("status")
    if status != "success":
        error_text = str(raw_result.get("error", "")).lower()
        if "timeout" in error_text or "timed out" in error_text:
            raise AgentTimeoutError("Agent execution timed out")
        if any(
            marker in error_text
            for marker in ("ollama", "model", "not running", "unavailable")
        ):
            raise AgentUnavailableError("Agent service is unavailable")
        raise AgentExecutionError("Agent execution failed")

    response = raw_result.get("final_answer")
    task_type = raw_result.get("task_type")
    if not isinstance(response, str) or not response.strip():
        raise AgentExecutionError("Agent response is missing")
    if response.strip() == "Report generation failed.":
        raise AgentUnavailableError("Agent service is unavailable")
    if task_type not in AGENT_TASK_TYPES:
        raise AgentExecutionError("Agent task type is invalid")

    execution_time = raw_result.get("execution_time_seconds", 0.0)
    if not isinstance(execution_time, (int, float)) or execution_time < 0:
        raise AgentExecutionError("Agent execution time is invalid")

    return AgentResult(
        status="success",
        response=response.strip(),
        task_type=task_type,
        citations=_normalize_citations(raw_result.get("citations")),
        steps=_normalize_steps(raw_result.get("steps_taken")),
        execution_time_seconds=float(execution_time),
        air_gapped=raw_result.get("air_gapped") is True,
    )


def _normalize_citations(value: object) -> list[AgentCitation]:
    if not isinstance(value, list):
        return []

    citations: list[AgentCitation] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        source = item.get("source")
        if not isinstance(source, str) or not source.strip():
            continue
        page = str(item.get("page", "N/A"))
        distance_value = item.get("distance")
        distance = (
            float(distance_value)
            if isinstance(distance_value, (int, float))
            else None
        )
        citations.append(
            AgentCitation(
                source=source.strip(),
                page=page,
                distance=distance,
            )
        )
    return citations


def _normalize_steps(value: object) -> list[AgentStep]:
    if not isinstance(value, list):
        return []

    steps: list[AgentStep] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        step = item.get("step")
        agent = item.get("agent")
        action = item.get("action")
        if (
            isinstance(step, int)
            and isinstance(agent, str)
            and isinstance(action, str)
        ):
            steps.append(
                AgentStep(
                    step=step,
                    agent=agent,
                    action=action,
                )
            )
    return steps
