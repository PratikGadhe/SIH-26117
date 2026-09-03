"""Backend-owned agent execution service."""

from app.integrations.agent import AgentExecutionError, AgentIntegrationError
from app.integrations.agent import AgentResult, AgentRunner


class AgentService:
    """Delegate one execution to the configured agent adapter."""

    def __init__(self, runner: AgentRunner) -> None:
        self._runner = runner

    def run(self, message: str) -> AgentResult:
        try:
            return self._runner.run(message)
        except AgentIntegrationError:
            raise
        except Exception as exc:
            raise AgentExecutionError("Agent execution failed") from exc
