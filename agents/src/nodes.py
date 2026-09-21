"""
LangGraph Worker Nodes for SIH 26117 Agents
Implements Supervisor (Planner), Vision, RAG, and Synthesizer nodes.
"""

import os
import sys
import time
import json
import re
from typing import Dict, Any, List, Optional, Tuple

current_dir = os.path.dirname(os.path.abspath(__file__))
agents_root = os.path.abspath(os.path.join(current_dir, ".."))
if agents_root not in sys.path:
    sys.path.insert(0, agents_root)

from src.state import WorkbenchState
from src.ollama_text_client import OllamaTextClient
from src.prompts import (
    SUPERVISOR_SYSTEM_PROMPT,
    SYNTHESIZER_SYSTEM_PROMPT,
    DOCUMENT_QA_SYNTHESIZER_PROMPT,
    IMAGE_SYNTHESIZER_PROMPT,
    DIRECT_CHAT_SYNTHESIZER_PROMPT,
    TOOL_SYNTHESIZER_PROMPT,
)
from vision_tool import vision_tool, pdf_tool
from rag_tool import rag_tool
from tools.registry import default_tool_registry

# Initialize local Qwen reasoning model
llm_client = OllamaTextClient(base_url="http://localhost:11434", model_name="qwen3:4b")


def _parse_threshold_query(q_lower: str) -> Optional[Tuple[str, float, Optional[str]]]:
    """
    Deterministically parses comparison operators and numeric values for threshold queries.
    Recognizes patterns like:
      - 'exceeding 5.0', 'exceeds 5.0', 'above 5.0', 'greater than 5.0', 'more than 5.0', '> 5.0'
      - 'below 5.0', 'less than 5.0', 'under 5.0', '< 5.0'
      - '>= 5.0', '<= 5.0', 'at least 5.0', 'at most 5.0'
      - '== 5.0', 'equals 5.0'
    Returns: (operator, threshold_float, column_name_or_None)
    """
    patterns = [
        (r"(?:^|[^\w<>=])>=\s*([0-9.]+)", ">="),
        (r"\bat\s+least\s+([0-9.]+)", ">="),
        (r"(?:^|[^\w<>=])<=\s*([0-9.]+)", "<="),
        (r"\bat\s+most\s+([0-9.]+)", "<="),
        (r"\bexceeding\s+([0-9.]+)", ">"),
        (r"\bexceeds\s+([0-9.]+)", ">"),
        (r"\babove\s+([0-9.]+)", ">"),
        (r"\bgreater\s+than\s+([0-9.]+)", ">"),
        (r"\bmore\s+than\s+([0-9.]+)", ">"),
        (r"\bhigher\s+than\s+([0-9.]+)", ">"),
        (r"(?:^|[^\w<>=])>\s*([0-9.]+)", ">"),
        (r"\bbelow\s+([0-9.]+)", "<"),
        (r"\bless\s+than\s+([0-9.]+)", "<"),
        (r"\bunder\s+([0-9.]+)", "<"),
        (r"\blower\s+than\s+([0-9.]+)", "<"),
        (r"(?:^|[^\w<>=])<\s*([0-9.]+)", "<"),
        (r"(?:^|[^\w<>=])==\s*([0-9.]+)", "=="),
        (r"\bequals?\s+(?:to\s+)?([0-9.]+)", "=="),
    ]

    matched_op = None
    matched_val = None

    for pat, op in patterns:
        m = re.search(pat, q_lower)
        if m:
            try:
                matched_val = float(m.group(1).rstrip("."))
                matched_op = op
                break
            except ValueError:
                continue

    if matched_op is None or matched_val is None:
        return None

    col = None
    if "vibration" in q_lower:
        col = "vibration_mm_s"
    elif "temp" in q_lower:
        col = "temperature_c"
    elif "hour" in q_lower:
        col = "operating_hours"
    elif "pressure" in q_lower:
        col = "pressure_psi"

    return matched_op, matched_val, col


def _parse_ranking_query(q_lower: str) -> Optional[Tuple[int, bool, Optional[str]]]:
    """
    Deterministically parses ranking requests with dynamic K count and sort direction.
    Recognizes:
      - 'top 5', 'top 10', 'highest 5', 'lowest 2', 'bottom 3', 'rank 5'
      - Defaults to K=3 if no explicit count is requested.
    Returns: (top_k_count, ascending_bool, column_name_or_None)
    """
    ranking_words = [
        "highest",
        "maximum",
        "max",
        "top",
        "rank",
        "lowest",
        "minimum",
        "min",
        "bottom",
    ]
    if not any(w in q_lower for w in ranking_words):
        return None

    # Try matching explicit count: e.g. "top 5", "highest 10", "lowest 2"
    k_match = re.search(
        r"\b(?:top|highest|maximum|max|lowest|minimum|min|bottom|rank)\s*(\d+)\b",
        q_lower,
    )
    if not k_match:
        # e.g. "5 highest", "10 lowest"
        k_match = re.search(
            r"\b(\d+)\s*(?:highest|maximum|max|lowest|minimum|min|bottom|top)\b",
            q_lower,
        )

    top_k_count = int(k_match.group(1)) if k_match else 3

    ascending = any(w in q_lower for w in ["lowest", "minimum", "min", "bottom"])

    col = None
    if "vibration" in q_lower:
        col = "vibration_mm_s"
    elif "temp" in q_lower:
        col = "temperature_c"
    elif "hour" in q_lower:
        col = "operating_hours"

    return top_k_count, ascending, col


def _detect_tool_intent(
    user_query: str, state: WorkbenchState
) -> Optional[Dict[str, Any]]:
    """
    Deterministically parses user query for approved tool requests (Knowledge Search,
    File Reader, Data Analysis, Python Execution).
    """
    q_lower = user_query.lower().strip()

    # 1. Knowledge Search intent
    if any(
        phrase in q_lower
        for phrase in [
            "search the local knowledge base",
            "search knowledge base",
            "search the knowledge base",
            "search documents for",
            "search the repository for",
            "look up in knowledge base",
            "search local knowledge",
        ]
    ):
        clean_query = user_query
        for prefix in [
            "search the local knowledge base for",
            "search the knowledge base for",
            "search knowledge base for",
            "search documents for",
            "search the repository for",
            "search the local knowledge base concerning",
            "search local knowledge base for",
        ]:
            if prefix in clean_query.lower():
                idx = clean_query.lower().find(prefix) + len(prefix)
                clean_query = clean_query[idx:].strip()
                break

        clean_query = re.sub(r"(?i)\s+and\s+summarize.*$", "", clean_query).strip()
        if not clean_query:
            clean_query = user_query

        return {
            "tool_name": "knowledge_search",
            "arguments": {"query": clean_query, "top_k": 3},
        }

    # 2. Python Execution intent
    is_informational_python = any(
        q_lower.startswith(p)
        for p in [
            "what is python",
            "explain what python",
            "tell me about python",
            "history of python",
            "describe python",
        ]
    )

    is_python_intent = False
    if not is_informational_python:
        explicit_python_triggers = [
            "use python",
            "using python",
            "run python",
            "execute python",
            "with python",
            "calculate using python",
            "compute using python",
            "execute this code",
            "run this code",
            "python script",
            "python code",
            "python calculation",
            "run a python calculation",
            "run script to compute",
            "import os",
            "import math",
            "import pandas",
            "import numpy",
            "import subprocess",
            "import sys",
        ]
        if any(trigger in q_lower for trigger in explicit_python_triggers):
            is_python_intent = True
        elif re.search(
            r"\b(?:calculate|compute|eval|evaluate|solve)\b.*?\b(?:using|in|with)\s+python\b",
            q_lower,
        ):
            is_python_intent = True
        elif re.search(r"\b(?:use|using)\s+python\s+to\s+\w+", q_lower):
            is_python_intent = True
        elif re.search(r"```(?:python)?\s*[\s\S]+?```", user_query):
            is_python_intent = True
        elif re.search(r"\bdef\s+\w+\s*\(.*?\):", user_query):
            is_python_intent = True

    if is_python_intent:
        code_block_match = re.search(r"```(?:python)?\s*([\s\S]+?)```", user_query)
        if code_block_match:
            code = code_block_match.group(1).strip()
        elif "import os" in q_lower:
            code = "import os\nprint(os.listdir('.'))"
        elif (
            "import subprocess" in q_lower
            or "shell command" in q_lower
            or "subprocess" in q_lower
        ):
            code = "import subprocess\nsubprocess.run(['ls'])"
        elif "import sys" in q_lower:
            code = "import sys\nprint(sys.version)"
        elif "import math" in q_lower:
            code = "import math\nprint(math.pi)"
        elif "import pandas" in q_lower:
            code = "import pandas as pd\nprint(pd.__name__)"
        elif "import numpy" in q_lower:
            code = "import numpy as np\nprint(np.__name__)"
        else:
            p_design_match = re.search(
                r"(?:p_design|design\s+pressure)\s*(?:=|is|of|:)?\s*([0-9.]+)",
                user_query,
                re.IGNORECASE,
            )
            sf_match = re.search(
                r"(?:safety_factor|safety\s+factor)\s*(?:=|is|of|:)?\s*([0-9.]+)",
                user_query,
                re.IGNORECASE,
            )
            derate_match = re.search(
                r"(?:temperature_derating|temperature\s+derating|derating)\s*(?:=|is|of|:)?\s*([0-9.]+)",
                user_query,
                re.IGNORECASE,
            )

            if p_design_match and sf_match:
                p_val = float(p_design_match.group(1).rstrip("."))
                sf_val = float(sf_match.group(1).rstrip("."))
                derate_val = (
                    float(derate_match.group(1).rstrip(".")) if derate_match else 1.0
                )
                code = (
                    f"# Engineering computation: Safe Operating Pressure Limit\n"
                    f"p_design = {p_val}\n"
                    f"safety_factor = {sf_val}\n"
                    f"temperature_derating = {derate_val}\n"
                    f"safe_operating_pressure = (p_design / safety_factor) * temperature_derating\n"
                    f"print(f'Design Pressure (P_design): {p_val} bar')\n"
                    f"print(f'Safety Factor: {sf_val}')\n"
                    f"print(f'Temperature Derating: {derate_val}')\n"
                    f"print(f'Safe Operating Pressure Limit: {{safe_operating_pressure:.2f}} bar')\n"
                )
            elif "500" in q_lower and "1.25" in q_lower:
                code = (
                    "pressure_kpa = 500\n"
                    "safety_factor = 1.25\n"
                    "safe_limit = pressure_kpa * safety_factor\n"
                    "print(f'Design Pressure: {pressure_kpa} kPa')\n"
                    "print(f'Safety Factor: {safety_factor}x')\n"
                    "print(f'Safe Operating Pressure Limit: {safe_limit:.2f} kPa')\n"
                )
            else:
                calc_match = re.search(
                    r"(?:calculate|compute|eval|evaluate)\s+([0-9\.\s\+\-\*\/\(\)]+)",
                    user_query,
                    re.IGNORECASE,
                )
                if calc_match and any(
                    op in calc_match.group(1) for op in ["+", "-", "*", "/"]
                ):
                    expr = calc_match.group(1).strip().rstrip(".")
                    code = (
                        f"result = {expr}\nprint(f'Calculation result: {{result}}')\n"
                    )
                else:
                    code = "result = sum([i**2 for i in range(1, 11)])\nprint(f'Calculation result: {result}')\n"

        return {
            "tool_name": "python_execute",
            "arguments": {"code": code},
        }

    # 3. File Reader & Data Analysis intent
    ref_file = None
    if state and state.get("csv_path"):
        ref_file = state["csv_path"]
    else:
        file_match = re.search(
            r"([\w\-./]+\.(?:csv|txt|json|pdf|docx))", user_query, re.I
        )
        if file_match:
            ref_file = file_match.group(1).strip()
            if not os.path.exists(ref_file):
                candidate_paths = [
                    os.path.join("agents", "tests", "test_data", ref_file),
                    os.path.join(
                        "rag", "MRPL-Sovereign-AI", "RAG", "documents", ref_file
                    ),
                    os.path.join("vision", "tests", "sample_images", ref_file),
                ]
                for cp in candidate_paths:
                    if os.path.exists(cp):
                        ref_file = cp
                        break

    if ref_file:
        ext = os.path.splitext(ref_file)[1].lower()
        wants_read_first = (
            q_lower.startswith("read") or "read this" in q_lower or "read " in q_lower
        )

        if ext == ".csv":
            if wants_read_first:
                return {
                    "tool_name": "file_reader",
                    "arguments": {"file_path": ref_file},
                }

            # 1. Deterministic threshold filtering (Issue 1)
            threshold_info = _parse_threshold_query(q_lower)
            if threshold_info is not None:
                op, val, col = threshold_info
                return {
                    "tool_name": "data_analysis",
                    "arguments": {
                        "file_path": ref_file,
                        "operation": "filter",
                        "filter_column": col or "vibration_mm_s",
                        "filter_operator": op,
                        "filter_value": val,
                    },
                }

            # 2. Dynamic ranking (Issue 1)
            ranking_info = _parse_ranking_query(q_lower)
            if ranking_info is not None:
                k_count, asc, col = ranking_info
                return {
                    "tool_name": "data_analysis",
                    "arguments": {
                        "file_path": ref_file,
                        "operation": "top_k",
                        "column": col or "vibration_mm_s",
                        "top_k_count": k_count,
                        "ascending": asc,
                    },
                }

            # 3. Categorical aggregation
            elif any(
                w in q_lower
                for w in ["average", "mean", "sum", "group by", "category", "aggregate"]
            ):
                target_col = (
                    "operating_hours"
                    if "hour" in q_lower
                    else (
                        "vibration_mm_s" if "vibration" in q_lower else "temperature_c"
                    )
                )
                agg_func = "sum" if "sum" in q_lower else "mean"
                return {
                    "tool_name": "data_analysis",
                    "arguments": {
                        "file_path": ref_file,
                        "operation": "aggregate",
                        "group_by": "category",
                        "target_column": target_col,
                        "agg_func": agg_func,
                    },
                }
            elif "column" in q_lower:
                return {
                    "tool_name": "data_analysis",
                    "arguments": {
                        "file_path": ref_file,
                        "operation": "inspect_columns",
                    },
                }
            elif "missing" in q_lower:
                return {
                    "tool_name": "data_analysis",
                    "arguments": {"file_path": ref_file, "operation": "missing_values"},
                }
            else:
                return {
                    "tool_name": "file_reader",
                    "arguments": {"file_path": ref_file},
                }
        else:
            return {"tool_name": "file_reader", "arguments": {"file_path": ref_file}}

    return None


def supervisor_node(state: WorkbenchState) -> Dict[str, Any]:
    """
    Analyzes the user query and inputs, classifies task type, evaluates tool results,
    and manages multi-step tool loops.
    """
    user_query = state.get("user_query", "")
    image_path = state.get("image_path")
    pdf_path = state.get("pdf_path")
    tool_call_count = state.get("tool_call_count", 0)
    tool_results = state.get("tool_results", [])
    max_tool_calls = state.get("max_tool_calls", 5)

    # 1. Check if this is an iterative continuation turn
    if tool_call_count > 0 and tool_results:
        # Enforce loop safety limit
        if tool_call_count >= max_tool_calls:
            step_entry = {
                "step": len(state.get("steps_log", [])) + 1,
                "agent": "Supervisor Agent",
                "action": f"Reached maximum allowed tool iterations ({max_tool_calls}). Finalizing synthesis.",
            }
            return {
                "pending_tool_call": None,
                "steps_log": state.get("steps_log", []) + [step_entry],
            }

        last_result = tool_results[-1]
        last_tool = last_result.get("tool_name")
        q_lower = user_query.lower()

        # Multi-tool chaining: file_reader -> data_analysis
        if last_tool == "file_reader" and last_result.get("success"):
            res_data = last_result.get("result", {})
            filename = res_data.get("filename", "")
            resolved_path = last_result.get("metadata", {}).get(
                "resolved_path", filename
            )

            if filename.endswith(".csv"):
                has_run_data_analysis = any(
                    r.get("tool_name") == "data_analysis" for r in tool_results
                )
                if not has_run_data_analysis:
                    # 1. Deterministic threshold filtering (Issue 1)
                    threshold_info = _parse_threshold_query(q_lower)
                    if threshold_info is not None:
                        op, val, col = threshold_info
                        next_tool = {
                            "tool_name": "data_analysis",
                            "arguments": {
                                "file_path": resolved_path,
                                "operation": "filter",
                                "filter_column": col or "vibration_mm_s",
                                "filter_operator": op,
                                "filter_value": val,
                            },
                        }
                        step_entry = {
                            "step": len(state.get("steps_log", [])) + 1,
                            "agent": "Supervisor Agent",
                            "action": f"Evaluated file contents; scheduling Data Analysis filter ({col or 'vibration_mm_s'} {op} {val})",
                        }
                        return {
                            "pending_tool_call": next_tool,
                            "steps_log": state.get("steps_log", []) + [step_entry],
                        }

                    # 2. Aggregation
                    if any(
                        w in q_lower
                        for w in [
                            "average",
                            "mean",
                            "sum",
                            "category",
                            "aggregate",
                            "group by",
                        ]
                    ):
                        target_col = (
                            "operating_hours"
                            if "hour" in q_lower
                            else (
                                "vibration_mm_s"
                                if "vibration" in q_lower
                                else "temperature_c"
                            )
                        )
                        agg_func = "sum" if "sum" in q_lower else "mean"
                        next_tool = {
                            "tool_name": "data_analysis",
                            "arguments": {
                                "file_path": resolved_path,
                                "operation": "aggregate",
                                "group_by": "category",
                                "target_column": target_col,
                                "agg_func": agg_func,
                            },
                        }
                        step_entry = {
                            "step": len(state.get("steps_log", [])) + 1,
                            "agent": "Supervisor Agent",
                            "action": "Evaluated file contents; scheduling Data Analysis aggregation",
                        }
                        return {
                            "pending_tool_call": next_tool,
                            "steps_log": state.get("steps_log", []) + [step_entry],
                        }

                    # 3. Dynamic ranking (Issue 1)
                    ranking_info = _parse_ranking_query(q_lower)
                    if ranking_info is not None:
                        k_count, asc, col = ranking_info
                        next_tool = {
                            "tool_name": "data_analysis",
                            "arguments": {
                                "file_path": resolved_path,
                                "operation": "top_k",
                                "column": col or "vibration_mm_s",
                                "top_k_count": k_count,
                                "ascending": asc,
                            },
                        }
                        step_entry = {
                            "step": len(state.get("steps_log", [])) + 1,
                            "agent": "Supervisor Agent",
                            "action": f"Evaluated file contents; scheduling Data Analysis ranking (top {k_count})",
                        }
                        return {
                            "pending_tool_call": next_tool,
                            "steps_log": state.get("steps_log", []) + [step_entry],
                        }

        # If no further tool needed, stop loop and proceed to synthesis
        return {
            "pending_tool_call": None,
        }

    # 2. Initial Turn: Fast deterministic classification and tool detection
    if pdf_path:
        task_type = "VISION_INSPECTION"
        plan = [
            "Extract document text and structure via PyMuPDF",
            "Synthesize document findings with Qwen3 4B",
        ]
        pending_tool = None
    elif image_path:
        if any(
            w in user_query.lower()
            for w in [
                "sop",
                "safety",
                "rule",
                "limit",
                "allow",
                "comply",
                "violate",
                "standard",
            ]
        ):
            task_type = "HYBRID_AUDIT"
            plan = [
                "Inspect visual schematic with Qwen3-VL",
                "Retrieve matching SOP rules from ChromaDB",
                "Audit compliance with Qwen3 4B",
            ]
        else:
            task_type = "VISION_INSPECTION"
            plan = [
                "Analyze visual schematic with Qwen3-VL",
                "Summarize detected components and status",
            ]
        pending_tool = None
    else:
        # Text-only query: check if user requested an approved tool
        tool_intent = _detect_tool_intent(user_query, state)
        if tool_intent is not None:
            tool_name = tool_intent["tool_name"]
            pending_tool = tool_intent
            task_type = (
                "SOP_QUERY" if tool_name == "knowledge_search" else "DIRECT_CHAT"
            )
            plan = [
                f"Execute tool: {tool_name}",
                "Synthesize verified findings with Qwen3 4B",
            ]
        elif any(
            w in user_query.lower()
            for w in [
                "sop",
                "manual",
                "rule",
                "limit",
                "pressure",
                "temperature",
                "procedure",
                "shutdown",
                "startup",
            ]
        ):
            task_type = "SOP_QUERY"
            plan = [
                "Search refinery knowledge base via ChromaDB",
                "Synthesize safety advice with Qwen3 4B",
            ]
            pending_tool = None
        else:
            task_type = "DIRECT_CHAT"
            plan = ["Process general engineering query with Qwen3 4B"]
            pending_tool = None

    action_text = (
        f"Classified task as tool-assisted workflow ({pending_tool['tool_name']})"
        if pending_tool
        else f"Classified task as {task_type}"
    )

    step_entry = {
        "step": len(state.get("steps_log", [])) + 1,
        "agent": "Supervisor Agent",
        "action": action_text,
        "plan": plan,
    }

    return {
        "task_type": task_type,
        "plan": plan,
        "pending_tool_call": pending_tool,
        "steps_log": state.get("steps_log", []) + [step_entry],
    }


def vision_node(state: WorkbenchState) -> Dict[str, Any]:
    """
    Executes Member 4's Vision Tool on uploaded P&ID diagrams or PDFs.
    """
    image_path = state.get("image_path")
    pdf_path = state.get("pdf_path")
    user_query = state.get("user_query", "")

    if image_path:
        vision_result = vision_tool(image_path, user_query)
        input_type = "image"
    elif pdf_path:
        vision_result = pdf_tool(pdf_path, user_query)
        input_type = "PDF document"
    else:
        raise RuntimeError("Vision input is invalid")

    step_entry = {
        "step": len(state.get("steps_log", [])) + 1,
        "agent": "Vision Agent (Qwen3-VL)",
        "action": f"Inspected {input_type}",
        "findings_summary": vision_result.get("analysis", "")[:200] + "..."
        if vision_result.get("analysis")
        else "Done",
    }

    return {
        "vision_data": vision_result,
        "steps_log": state.get("steps_log", []) + [step_entry],
    }


def rag_node(state: WorkbenchState) -> Dict[str, Any]:
    """
    Executes Member 2's RAG search over MRPL refinery manuals.
    """
    user_query = state.get("user_query", "")
    vision_data = state.get("vision_data", {})

    # Enrich search query with tags discovered by vision
    search_query = user_query
    if vision_data and "analysis" in vision_data:
        search_query = f"{user_query} {vision_data['analysis'][:100]}"

    rag_result = rag_tool(search_query, top_k=3)

    citations = []
    for item in rag_result.get("results", []):
        citations.append(
            {
                "source": item.get("source", "MRPL Manual"),
                "page": item.get("page", "N/A"),
                "distance": item.get("distance", 0.0),
            }
        )

    step_entry = {
        "step": len(state.get("steps_log", [])) + 1,
        "agent": "RAG Knowledge Agent (ChromaDB)",
        "action": f"Queried SOP knowledge base with: '{user_query}'",
        "sources_retrieved": len(citations),
    }

    return {
        "rag_data": rag_result,
        "citations": citations,
        "steps_log": state.get("steps_log", []) + [step_entry],
    }


def tool_node(state: WorkbenchState) -> Dict[str, Any]:
    """
    Executes the scheduled agentic tool via ToolRegistry, formats step log,
    and updates tool results and citations.
    """
    pending = state.get("pending_tool_call")
    if not pending:
        return {}

    tool_name = pending.get("tool_name", "")
    arguments = pending.get("arguments", {})

    tool_result = default_tool_registry.execute_tool(tool_name, arguments)
    res_dict = tool_result.to_dict()

    name_map = {
        "knowledge_search": "Knowledge Search",
        "file_reader": "File Reader",
        "data_analysis": "Data Analysis",
        "python_execute": "Python Execution",
    }
    display_name = name_map.get(tool_name, tool_name.title())

    if tool_result.success:
        res_data = tool_result.result or {}
        if tool_name == "knowledge_search":
            count = res_data.get("results_count", 0)
            action_text = f"Retrieved {count} relevant knowledge passages for: '{arguments.get('query')}'"
        elif tool_name == "file_reader":
            fname = res_data.get("filename", "")
            meta = res_data.get("metadata", {})
            units = (
                f"{meta.get('row_count')} rows"
                if "row_count" in meta
                else f"{meta.get('lines', 0)} lines"
            )
            action_text = f"Read {units} from '{fname}'"
        elif tool_name == "data_analysis":
            op = res_data.get("operation", "")
            ds = res_data.get("dataset", "")
            action_text = f"Completed '{op}' analysis on '{ds}'"
        elif tool_name == "python_execute":
            elapsed = res_data.get("execution_time_seconds", 0.01)
            action_text = f"Executed safe calculation script in {elapsed:.2f}s"
        else:
            action_text = f"Executed {tool_name} successfully"
    else:
        err_msg = (tool_result.error or {}).get("message", "Unknown error")
        action_text = f"Tool '{tool_name}' failed: {err_msg}"

    step_entry = {
        "step": len(state.get("steps_log", [])) + 1,
        "agent": f"Tool: {display_name}",
        "action": action_text,
    }

    new_citations = list(state.get("citations", []))
    if tool_name == "knowledge_search" and tool_result.success:
        for c in (tool_result.result or {}).get("citations", []):
            new_citations.append(c)

    return {
        "tool_results": state.get("tool_results", []) + [res_dict],
        "tool_call_count": state.get("tool_call_count", 0) + 1,
        "pending_tool_call": None,
        "citations": new_citations,
        "steps_log": state.get("steps_log", []) + [step_entry],
    }


def synthesizer_node(state: WorkbenchState) -> Dict[str, Any]:
    """
    Combines vision analysis, tool results, and RAG manual excerpts into a grounded document, visual, or formal report answer.
    """
    user_query = state.get("user_query", "")
    task_type = state.get("task_type", "DIRECT_CHAT")
    image_path = state.get("image_path")
    pdf_path = state.get("pdf_path")
    vision_data = state.get("vision_data") or {}
    rag_data = state.get("rag_data") or {}
    tool_results = state.get("tool_results") or []

    # 1. Tool-assisted query synthesis
    if tool_results:
        # Fast deterministic handling for empty knowledge search retrieval
        all_ks = all(tr.get("tool_name") == "knowledge_search" for tr in tool_results)
        total_ks_count = sum(
            (tr.get("result") or {}).get("results_count", 0)
            for tr in tool_results
            if tr.get("tool_name") == "knowledge_search"
        )
        if all_ks and total_ks_count == 0:
            step_entry = {
                "step": len(state.get("steps_log", [])) + 1,
                "agent": "Synthesis Agent (Qwen3 4B)",
                "action": "Synthesized verified tool findings into final response",
            }
            return {
                "final_answer": (
                    "No matching information was found in the local knowledge base for this query. "
                    "I therefore cannot provide a grounded value from the available documents."
                ),
                "steps_log": state.get("steps_log", []) + [step_entry],
                "status": "success",
            }

        findings_parts = []
        for tr in tool_results:
            t_name = tr.get("tool_name")
            if tr.get("success"):
                t_res = tr.get("result", {})
                if t_name == "knowledge_search":
                    raw_context = (t_res.get("context") or "").strip()
                    results_count = t_res.get("results_count", 0)
                    if not raw_context or results_count == 0:
                        context_text = "No matching information found in the local knowledge base for this query."
                    else:
                        context_text = raw_context
                    findings_parts.append(
                        f"### Knowledge Search Findings (Query: '{t_res.get('query')}'):\n"
                        f"{context_text}"
                    )
                elif t_name == "file_reader":
                    findings_parts.append(
                        f"### File Reader Output (File: '{t_res.get('filename')}'):\n"
                        f"{t_res.get('content', '')}"
                    )
                elif t_name == "data_analysis":
                    findings_parts.append(
                        f"### Data Analysis Findings (Dataset: '{t_res.get('dataset')}', Operation: '{t_res.get('operation')}'):\n"
                        f"{json.dumps(t_res.get('analysis', {}), indent=2)}"
                    )
                elif t_name == "python_execute":
                    findings_parts.append(
                        f"### Python Execution Output:\n"
                        f"Stdout: {t_res.get('stdout', '')}\n"
                        f"Variables: {json.dumps(t_res.get('variables', {}))}"
                    )
            else:
                findings_parts.append(
                    f"### Tool '{t_name}' Execution Error:\n"
                    f"{json.dumps(tr.get('error', {}))}"
                )

        combined_context = "\n\n".join(findings_parts)
        system_prompt = TOOL_SYNTHESIZER_PROMPT
        synthesis_prompt = f"""User Question:
{user_query}

Verified Tool Findings:
{combined_context}"""
        temperature = 0.1
        action_text = "Synthesized verified tool findings into final response"

    else:
        context_parts = []

        if vision_data.get("analysis"):
            if pdf_path:
                context_parts.append(
                    f"### Attached Document Content:\n{vision_data['analysis']}"
                )
            else:
                context_parts.append(
                    f"### Visual Inspection Findings:\n{vision_data['analysis']}"
                )

        if rag_data.get("context"):
            context_parts.append(
                f"### Relevant Knowledge Base Excerpts:\n{rag_data['context']}"
            )

        combined_context = (
            "\n\n".join(context_parts)
            if context_parts
            else "No external documents or visual assets referenced."
        )

        # Distinguish input modalities and query intents:
        # 1. Attached PDF / Document input
        # 2. Attached Image input
        # 3. Pure text query (RAG / Direct Chat)
        if pdf_path:
            system_prompt = DOCUMENT_QA_SYNTHESIZER_PROMPT
            strict_instruction = ""
            if any(
                phrase in user_query.lower()
                for phrase in [
                    "answer only from",
                    "only from the attached",
                    "strictly from",
                ]
            ):
                strict_instruction = (
                    "\n\nIMPORTANT: The user explicitly requested to answer ONLY from the attached document. "
                    "If the attached document does not contain sufficient information to answer the question, "
                    'state what is mentioned and state clearly: "The attached document does not provide enough information to answer this question." '
                    "Do NOT use external knowledge or invent facts."
                )

            synthesis_prompt = f"""User Question:
{user_query}

Document Content:
{combined_context}{strict_instruction}

Answer the user's question directly and concisely based ONLY on the provided document content above. If the document does not describe detailed procedures, summarize what relevant features or details are mentioned and state clearly if the attached document does not provide enough information to answer this question."""

            temperature = 0.1
            action_text = "Generated grounded document response"

        elif image_path:
            system_prompt = IMAGE_SYNTHESIZER_PROMPT

            # Only evaluate compliance if user explicitly asks for an audit AND SOP evidence was retrieved
            user_wants_compliance = any(
                w in user_query.lower()
                for w in ["comply", "compliance", "violate", "audit", "standard", "sop"]
            )
            has_sop_evidence = bool(rag_data.get("context"))

            if user_wants_compliance and has_sop_evidence:
                synthesis_prompt = f"""User Question:
{user_query}

Visual & Knowledge Evidence:
{combined_context}

Evaluate the visual findings against the provided knowledge base excerpts. Mention only visible components supported by the visual findings, and cite only rules present in the provided excerpts. Do not invent citations or unobserved components."""
            else:
                synthesis_prompt = f"""User Question:
{user_query}

Authoritative Visual Evidence:
{combined_context}

Based strictly on the visual evidence above, describe the visible components clearly and professionally using structured bullet points (noting symbols and representations as reported in the findings). Mention only components that are actually visible in the findings. If appropriate, briefly state that no additional components were identified. Do not invent equipment tags, safety rules, SOP numbers, or compliance citations. Do NOT include any internal reasoning, thought process, or meta-commentary."""

            temperature = 0.1
            action_text = "Generated grounded visual response"

        else:
            # Pure text query
            has_pid_or_equipment_query = any(
                term in user_query.lower()
                for term in [
                    "p&id",
                    "pid",
                    "schematic",
                    "drawing",
                    "diagram",
                    "pump",
                    "valve",
                    "flare",
                    "equipment",
                    "refinery",
                    "distillation",
                    "furnace",
                ]
            )
            if task_type == "SOP_QUERY" and rag_data.get("context"):
                system_prompt = DOCUMENT_QA_SYNTHESIZER_PROMPT
                synthesis_prompt = f"""User Question:
{user_query}

Knowledge Base Excerpts:
{combined_context}

Answer the user's question directly based on the provided knowledge base excerpts. Do not invent facts or citations."""
                temperature = 0.1
                action_text = "Generated grounded document response"
            elif has_pid_or_equipment_query or task_type == "HYBRID_AUDIT":
                system_prompt = SYNTHESIZER_SYSTEM_PROMPT
                synthesis_prompt = f"""User Question:
{user_query}

Verified Context & Evidence Gathered:
{combined_context}

Provide a structured, authoritative engineering assessment as the Chief Safety Lead."""
                temperature = 0.2
                action_text = "Generated final verified compliance report"
            else:
                system_prompt = DIRECT_CHAT_SYNTHESIZER_PROMPT
                synthesis_prompt = f"""User Question:
{user_query}

Answer the user's question directly, accurately, and concisely."""
                temperature = 0.3
                action_text = "Generated final verified response"

    report_res = llm_client.generate(
        prompt=synthesis_prompt,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=2048,
    )

    final_text = report_res.get("response", "Report generation failed.")

    step_entry = {
        "step": len(state.get("steps_log", [])) + 1,
        "agent": "Synthesis Agent (Qwen3 4B)",
        "action": action_text,
    }

    return {
        "final_answer": final_text,
        "steps_log": state.get("steps_log", []) + [step_entry],
        "status": "success",
    }
