"""
Base interfaces and result contracts for VYASA agentic tools.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ToolResult:
    """
    Standardized execution contract returned by every VYASA tool.
    """

    success: bool
    tool_name: str
    result: Any = None
    error: Optional[Dict[str, str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "tool_name": self.tool_name,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }

    @classmethod
    def success_result(
        cls,
        tool_name: str,
        result: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ToolResult:
        return cls(
            success=True,
            tool_name=tool_name,
            result=result,
            error=None,
            metadata=metadata or {},
        )

    @classmethod
    def failure_result(
        cls,
        tool_name: str,
        error_code: str,
        error_message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ToolResult:
        return cls(
            success=False,
            tool_name=tool_name,
            result=None,
            error={"code": error_code, "message": error_message},
            metadata=metadata or {},
        )


class BaseTool(ABC):
    """
    Abstract base class for all approved VYASA agentic tools.
    """

    name: str = ""
    description: str = ""
    parameters_schema: Dict[str, Any] = {}

    @abstractmethod
    def execute(self, **kwargs: Any) -> ToolResult:
        """
        Execute the tool with validated arguments.
        Must never raise unhandled exceptions; return ToolResult.failure_result instead.
        """
        raise NotImplementedError

    def get_schema(self) -> Dict[str, Any]:
        """
        Return tool metadata and parameter schema.
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters_schema,
        }
