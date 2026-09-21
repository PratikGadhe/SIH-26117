"""
Explicit Tool Registry for VYASA Agentic Runtime.
Defines the strict set of approved tools and dispatches execution requests.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

current_dir = os.path.dirname(os.path.abspath(__file__))
agents_root = os.path.abspath(os.path.join(current_dir, ".."))
if agents_root not in sys.path:
    sys.path.insert(0, agents_root)

from tools.base import BaseTool, ToolResult
from tools.knowledge_search import KnowledgeSearchTool
from tools.file_reader import FileReaderTool
from tools.data_analysis import DataAnalysisTool
from tools.python_execution import PythonExecutionTool


class ToolRegistry:
    """
    Explicit, closed tool registry for the sovereign workbench.
    Does not allow dynamic plugin loading or arbitrary code imports.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {
            "knowledge_search": KnowledgeSearchTool(),
            "file_reader": FileReaderTool(),
            "data_analysis": DataAnalysisTool(),
            "python_execute": PythonExecutionTool(),
        }

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Return tool instance by name if registered."""
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """Return metadata and schemas for all registered tools."""
        return [tool.get_schema() for tool in self._tools.values()]

    def list_tool_names(self) -> List[str]:
        """Return registered tool identifiers."""
        return list(self._tools.keys())

    def execute_tool(self, name: str, arguments: Dict[str, Any]) -> ToolResult:
        """
        Execute an approved tool by name with validated arguments.
        Rejects unknown tools safely with a structured contract.
        """
        tool = self.get_tool(name)
        if tool is None:
            available = ", ".join(self.list_tool_names())
            return ToolResult.failure_result(
                name,
                "UNKNOWN_TOOL",
                f"Tool '{name}' is not registered in VYASA runtime. Available tools: {available}.",
            )

        try:
            return tool.execute(**arguments)
        except Exception as e:
            return ToolResult.failure_result(
                name,
                "TOOL_CRASH",
                f"Unhandled tool crash in '{name}': {str(e)}",
            )


# Global singleton registry instance
default_tool_registry = ToolRegistry()
