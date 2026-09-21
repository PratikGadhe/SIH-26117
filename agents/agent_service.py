"""
Master Agent Service Interface for SIH 26117
Public entrypoint called by Member 1 (FastAPI backend) to execute multi-agent workflows.
"""

import os
import sys
import time
from typing import Dict, Any, Optional

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from src.state import WorkbenchState
from src.graph import agent_graph


def run_agentic_workflow(
    user_query: str,
    image_path: Optional[str] = None,
    pdf_path: Optional[str] = None,
    csv_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes the Sovereign Multi-Agent LangGraph workflow.

    Args:
        user_query: The engineer's question or instruction.
        image_path: Optional file path to a P&ID diagram, schematic, or equipment photo.
        pdf_path: Optional file path to a technical document or PDF manual.
        csv_path: Optional file path to a structured CSV data table.

    Returns:
        Structured response dictionary matching the master API contract.
    """
    start_time = time.time()

    initial_state: WorkbenchState = {
        "user_query": user_query,
        "image_path": image_path,
        "pdf_path": pdf_path,
        "csv_path": csv_path,
        "task_type": "DIRECT_CHAT",
        "plan": [],
        "vision_data": None,
        "rag_data": None,
        "steps_log": [],
        "citations": [],
        "final_answer": "",
        "status": "in_progress",
        "pending_tool_call": None,
        "tool_results": [],
        "tool_call_count": 0,
        "max_tool_calls": 5,
    }

    try:
        final_state = agent_graph.invoke(initial_state)
        elapsed_seconds = round(time.time() - start_time, 2)

        return {
            "status": final_state.get("status", "success"),
            "task_type": final_state.get("task_type"),
            "final_answer": final_state.get("final_answer"),
            "citations": final_state.get("citations", []),
            "steps_taken": final_state.get("steps_log", []),
            "execution_time_seconds": elapsed_seconds,
            "air_gapped": True,
        }

    except Exception as e:
        elapsed_seconds = round(time.time() - start_time, 2)
        return {
            "status": "error",
            "error": str(e),
            "final_answer": f"Agent workflow encountered an error: {str(e)}",
            "citations": [],
            "steps_taken": initial_state.get("steps_log", []),
            "execution_time_seconds": elapsed_seconds,
            "air_gapped": True,
        }


if __name__ == "__main__":
    print("Testing Agent Service CLI:")
    res = run_agentic_workflow(
        "What is the primary function of a flare stack in an oil refinery?"
    )
    print(res["final_answer"])
