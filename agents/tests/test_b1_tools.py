"""
Comprehensive unit and integration test suite for VYASA Phase B1 Agentic Tool Runtime.
Tests:
- Knowledge Search tool
- Safe File Reader tool
- Data Analysis tool
- Controlled Python Execution tool
- Tool Registry
- LangGraph integration, iterative tool loops, loop limits, and step logging
"""

import os
from pathlib import Path
import sys
import tempfile
import pytest

# Ensure agents/ is in Python path
agents_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if agents_root not in sys.path:
    sys.path.insert(0, agents_root)

project_root = os.path.abspath(os.path.join(agents_root, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from tools.base import ToolResult
from tools.knowledge_search import KnowledgeSearchTool
from tools.file_reader import FileReaderTool, validate_and_resolve_path
from tools.data_analysis import DataAnalysisTool
from tools.python_execution import PythonExecutionTool
from tools.registry import ToolRegistry, default_tool_registry
from src.state import WorkbenchState
from src.nodes import (
    supervisor_node,
    tool_node,
    synthesizer_node,
    _parse_threshold_query,
    _parse_ranking_query,
)
from src.graph import route_decision


# Test fixtures directory
FIXTURES_DIR = os.path.join(agents_root, "tests", "test_data")
SAMPLE_CSV = os.path.join(FIXTURES_DIR, "sample_equipment.csv")
SAMPLE_TXT = os.path.join(FIXTURES_DIR, "sample_notes.txt")
SAMPLE_JSON = os.path.join(FIXTURES_DIR, "sample_config.json")


# ==============================================================================
# 1. KNOWLEDGE SEARCH TOOL TESTS
# ==============================================================================


def test_knowledge_search_valid_query(monkeypatch):
    tool = KnowledgeSearchTool()

    fake_rag_result = {
        "status": "success",
        "query": "flare stack",
        "results": [
            {
                "source": "SOP-101.pdf",
                "page": "5",
                "content": "Flare stack rules",
                "distance": 0.12,
            },
            {
                "source": "SOP-102.pdf",
                "page": "8",
                "content": "Ignition limits",
                "distance": 0.18,
            },
        ],
        "context": "Flare stack rules\n\nIgnition limits",
        "engine": "ChromaDB + SentenceTransformers",
    }

    import rag_tool

    monkeypatch.setattr(rag_tool, "rag_tool", lambda query, top_k=3: fake_rag_result)

    result = tool.execute(query="flare stack", top_k=2)

    assert result.success is True
    assert result.tool_name == "knowledge_search"
    assert result.result["results_count"] == 2
    assert len(result.result["citations"]) == 2
    assert result.result["citations"][0]["source"] == "SOP-101.pdf"
    assert result.result["citations"][0]["page"] == "5"
    assert result.metadata["top_k"] == 2


def test_knowledge_search_empty_query():
    tool = KnowledgeSearchTool()
    result = tool.execute(query="   ")

    assert result.success is False
    assert result.error["code"] == "INVALID_QUERY"
    assert "non-empty string" in result.error["message"]


def test_knowledge_search_rag_unavailable(monkeypatch):
    tool = KnowledgeSearchTool()

    import rag_tool

    def fail_rag(*args, **kwargs):
        raise rag_tool.RAGUnavailableError("ChromaDB connection refused")

    monkeypatch.setattr(rag_tool, "rag_tool", fail_rag)

    result = tool.execute(query="pump limits")

    assert result.success is False
    assert result.error["code"] == "RAG_UNAVAILABLE"
    assert "unavailable" in result.error["message"]


def test_knowledge_search_top_k_clamping(monkeypatch):
    tool = KnowledgeSearchTool()

    recorded_top_k = []
    import rag_tool

    def mock_rag(query, top_k=3):
        recorded_top_k.append(top_k)
        return {"status": "success", "results": [], "context": "", "engine": "ChromaDB"}

    monkeypatch.setattr(rag_tool, "rag_tool", mock_rag)

    tool.execute(query="test", top_k=99)
    assert recorded_top_k[-1] == 10  # Clamped to 10

    tool.execute(query="test", top_k=-5)
    assert recorded_top_k[-1] == 1  # Clamped to 1


# ==============================================================================
# 2. SAFE FILE READER TOOL TESTS
# ==============================================================================


def test_file_reader_valid_txt():
    tool = FileReaderTool()
    result = tool.execute(file_path=SAMPLE_TXT)

    assert result.success is True
    assert result.result["filename"] == "sample_notes.txt"
    assert result.result["file_type"] == "txt"
    assert "P-102" in result.result["content"]
    assert result.result["metadata"]["lines"] > 0


def test_file_reader_valid_csv():
    tool = FileReaderTool()
    result = tool.execute(file_path=SAMPLE_CSV)

    assert result.success is True
    assert result.result["filename"] == "sample_equipment.csv"
    assert result.result["file_type"] == "csv"
    assert "equipment_id,category" in result.result["content"]
    assert result.result["metadata"]["row_count"] == 8


def test_file_reader_csv_trailing_newlines_and_empty_rows(tmp_path):
    csv_file = tmp_path / "equipment_test.csv"
    csv_file.write_text("id,name,value\n1,pump,10\n2,valve,20\n3,compressor,30\n\n\n")
    tool = FileReaderTool()
    result = tool.execute(file_path=str(csv_file))

    assert result.success is True
    assert result.result["metadata"]["row_count"] == 3
    assert result.result["metadata"]["header"] == "id,name,value"


def test_file_reader_valid_json():
    tool = FileReaderTool()
    result = tool.execute(file_path=SAMPLE_JSON)

    assert result.success is True
    assert result.result["filename"] == "sample_config.json"
    assert result.result["file_type"] == "json"
    assert "vibration_critical_mm_s" in result.result["content"]


def test_file_reader_path_traversal_rejection():
    tool = FileReaderTool()
    # Traversal attempting to escape workspace
    result = tool.execute(file_path="../../etc/passwd")

    assert result.success is False
    assert result.error["code"] == "SECURITY_VIOLATION"
    assert "Access denied" in result.error["message"]


def test_file_reader_dot_env_rejection():
    tool = FileReaderTool()
    result = tool.execute(file_path=".env")

    assert result.success is False
    assert result.error["code"] == "SECURITY_VIOLATION"
    assert "Access denied" in result.error["message"]


def test_file_reader_forbidden_extension():
    tool = FileReaderTool()
    result = tool.execute(file_path="cognivault.db")

    assert result.success is False
    assert result.error["code"] == "SECURITY_VIOLATION"


def test_file_reader_unsupported_extension(tmp_path):
    unsupported = tmp_path / "test.xyz"
    unsupported.write_text("dummy")

    canonical, err = validate_and_resolve_path(str(unsupported))
    assert canonical is None
    assert "Unsupported file format" in err


def test_file_reader_missing_file():
    tool = FileReaderTool()
    result = tool.execute(file_path="non_existent_document.txt")

    assert result.success is False
    assert result.error["code"] == "INVALID_FILE"
    assert "File not found" in result.error["message"]


# ==============================================================================
# 3. DATA ANALYSIS TOOL TESTS
# ==============================================================================


def test_data_analysis_inspect_columns():
    tool = DataAnalysisTool()
    result = tool.execute(file_path=SAMPLE_CSV, operation="inspect_columns")

    assert result.success is True
    assert result.result["operation"] == "inspect_columns"
    assert "equipment_id" in result.result["analysis"]["columns"]
    assert "vibration_mm_s" in result.result["analysis"]["columns"]
    assert result.result["analysis"]["row_count"] == 8
    assert len(result.result["analysis"]["sample_rows"]) <= 3


def test_data_analysis_row_count():
    tool = DataAnalysisTool()
    result = tool.execute(file_path=SAMPLE_CSV, operation="row_count")

    assert result.success is True
    assert result.result["analysis"]["total_rows"] == 8
    assert result.result["analysis"]["total_columns"] == 6


def test_data_analysis_missing_values():
    tool = DataAnalysisTool()
    result = tool.execute(file_path=SAMPLE_CSV, operation="missing_values")

    assert result.success is True
    report = result.result["analysis"]["missing_by_column"]
    assert "equipment_id" in report
    assert report["equipment_id"]["missing_count"] == 0


def test_data_analysis_numeric_summary():
    tool = DataAnalysisTool()
    result = tool.execute(
        file_path=SAMPLE_CSV, operation="numeric_summary", column="vibration_mm_s"
    )

    assert result.success is True
    summary = result.result["analysis"]["summaries"]["vibration_mm_s"]
    assert summary["count"] == 8
    assert summary["min"] == 0.4
    assert summary["max"] == 7.9
    assert summary["mean"] > 0


def test_data_analysis_filter():
    tool = DataAnalysisTool()
    result = tool.execute(
        file_path=SAMPLE_CSV,
        operation="filter",
        filter_column="status",
        filter_operator="equals",
        filter_value="CRITICAL",
    )

    assert result.success is True
    assert result.result["analysis"]["matching_count"] == 1
    assert result.result["analysis"]["rows_preview"][0]["equipment_id"] == "C-202"


def test_data_analysis_aggregate():
    tool = DataAnalysisTool()
    result = tool.execute(
        file_path=SAMPLE_CSV,
        operation="aggregate",
        group_by="category",
        target_column="operating_hours",
        agg_func="mean",
    )

    assert result.success is True
    res = result.result["analysis"]["results"]
    assert "Pump" in res
    assert "Compressor" in res
    # Compressor: (4500 + 9820) / 2 = 7160.0
    assert res["Compressor"] == 7160.0


def test_data_analysis_top_k():
    tool = DataAnalysisTool()
    result = tool.execute(
        file_path=SAMPLE_CSV,
        operation="top_k",
        column="vibration_mm_s",
        top_k_count=1,
        ascending=False,
    )

    assert result.success is True
    top_record = result.result["analysis"]["top_records"][0]
    assert top_record["equipment_id"] == "C-202"
    assert float(top_record["vibration_mm_s"]) == 7.9


def test_data_analysis_invalid_operation():
    tool = DataAnalysisTool()
    result = tool.execute(file_path=SAMPLE_CSV, operation="drop_table")

    assert result.success is False
    assert result.error["code"] == "UNKNOWN_OPERATION"


def test_data_analysis_invalid_column():
    tool = DataAnalysisTool()
    result = tool.execute(
        file_path=SAMPLE_CSV, operation="numeric_summary", column="non_existent_col"
    )

    assert result.success is False
    assert result.error["code"] == "ARGUMENT_ERROR"


# ==============================================================================
# 4. CONTROLLED PYTHON EXECUTION TOOL TESTS
# ==============================================================================


def test_python_execute_safe_calculation():
    tool = PythonExecutionTool()
    code = """
import math
radius = 4.5
area = math.pi * radius**2
print(f"Area: {area:.2f}")
"""
    result = tool.execute(code=code)

    assert result.success is True
    assert "Area: 63.62" in result.result["stdout"]
    assert result.result["variables"]["radius"] == 4.5


def test_python_execute_blocks_os_import():
    tool = PythonExecutionTool()
    code = "import os\nprint(os.listdir('.'))"
    result = tool.execute(code=code)

    assert result.success is False
    assert result.error["code"] == "SECURITY_VIOLATION"
    assert "prohibited" in result.error["message"]


def test_python_execute_blocks_subprocess():
    tool = PythonExecutionTool()
    code = "import subprocess\nsubprocess.run(['ls'])"
    result = tool.execute(code=code)

    assert result.success is False
    assert result.error["code"] == "SECURITY_VIOLATION"


def test_python_execute_blocks_open():
    tool = PythonExecutionTool()
    code = "f = open('/etc/passwd', 'r')\nprint(f.read())"
    result = tool.execute(code=code)

    assert result.success is False
    assert result.error["code"] == "SECURITY_VIOLATION"
    assert "open()" in result.error["message"]


def test_python_execute_blocks_eval_exec():
    tool = PythonExecutionTool()
    code = "eval('1 + 1')"
    result = tool.execute(code=code)

    assert result.success is False
    assert result.error["code"] == "SECURITY_VIOLATION"


def test_python_execute_blocks_network():
    tool = PythonExecutionTool()
    code = "import urllib.request\nurllib.request.urlopen('http://example.com')"
    result = tool.execute(code=code)

    assert result.success is False
    assert result.error["code"] == "SECURITY_VIOLATION"


def test_python_execute_timeout():
    tool = PythonExecutionTool()
    code = """
import time
# Emulate long running calculation without sleep
val = 0
for i in range(100_000_000):
    val += i
"""
    # Use very small timeout to verify trigger
    result = tool.execute(code=code, timeout_seconds=0.1)

    assert result.success is False
    assert result.error["code"] == "TIMEOUT"


def test_python_execute_syntax_error():
    tool = PythonExecutionTool()
    code = "def invalid syntax {::"
    result = tool.execute(code=code)

    assert result.success is False
    assert result.error["code"] == "SYNTAX_ERROR"


# ==============================================================================
# 5. TOOL REGISTRY TESTS
# ==============================================================================


def test_tool_registry_registered_tools():
    registry = ToolRegistry()
    names = registry.list_tool_names()

    assert "knowledge_search" in names
    assert "file_reader" in names
    assert "data_analysis" in names
    assert "python_execute" in names


def test_tool_registry_unknown_tool():
    registry = ToolRegistry()
    result = registry.execute_tool("malicious_shell", {"cmd": "rm -rf"})

    assert result.success is False
    assert result.error["code"] == "UNKNOWN_TOOL"


def test_tool_registry_list_tools_schema():
    registry = ToolRegistry()
    schemas = registry.list_tools()

    assert len(schemas) == 4
    for schema in schemas:
        assert "name" in schema
        assert "description" in schema
        assert "parameters" in schema


# ==============================================================================
# 6. LANGGRAPH WORKFLOW & ITERATIVE LOOP TESTS
# ==============================================================================


def test_supervisor_routes_to_knowledge_search():
    state: WorkbenchState = {
        "user_query": "Search the local knowledge base for flare stack safety rules and summarize the result with sources.",
        "image_path": None,
        "pdf_path": None,
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

    result = supervisor_node(state)
    assert result["pending_tool_call"] is not None
    assert result["pending_tool_call"]["tool_name"] == "knowledge_search"

    next_node = route_decision({**state, **result})
    assert next_node == "tool_node"


def test_supervisor_routes_to_file_reader():
    state: WorkbenchState = {
        "user_query": f"Read {SAMPLE_TXT} and tell me what is observed.",
        "image_path": None,
        "pdf_path": None,
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

    result = supervisor_node(state)
    assert result["pending_tool_call"] is not None
    assert result["pending_tool_call"]["tool_name"] == "file_reader"

    next_node = route_decision({**state, **result})
    assert next_node == "tool_node"


def test_supervisor_routes_to_data_analysis():
    state: WorkbenchState = {
        "user_query": f"Analyze this dataset {SAMPLE_CSV} and identify the equipment with the highest recorded vibration.",
        "image_path": None,
        "pdf_path": None,
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

    result = supervisor_node(state)
    assert result["pending_tool_call"] is not None
    assert result["pending_tool_call"]["tool_name"] == "data_analysis"
    assert result["pending_tool_call"]["arguments"]["operation"] == "top_k"


def test_supervisor_multi_tool_chaining():
    # Simulate turn 2 after file_reader has read sample_equipment.csv
    file_result = {
        "success": True,
        "tool_name": "file_reader",
        "result": {
            "filename": "sample_equipment.csv",
            "file_type": "csv",
            "content": "equipment_id,category...",
        },
        "metadata": {"resolved_path": SAMPLE_CSV},
    }

    state: WorkbenchState = {
        "user_query": "Read sample_equipment.csv and calculate the average operating hours for each equipment category.",
        "image_path": None,
        "pdf_path": None,
        "task_type": "DIRECT_CHAT",
        "plan": [],
        "vision_data": None,
        "rag_data": None,
        "steps_log": [{"step": 1, "agent": "Supervisor", "action": "start"}],
        "citations": [],
        "final_answer": "",
        "status": "in_progress",
        "pending_tool_call": None,
        "tool_results": [file_result],
        "tool_call_count": 1,
        "max_tool_calls": 5,
    }

    # Supervisor should evaluate turn 2 and schedule data_analysis aggregation
    turn2_result = supervisor_node(state)
    assert turn2_result["pending_tool_call"] is not None
    assert turn2_result["pending_tool_call"]["tool_name"] == "data_analysis"
    assert turn2_result["pending_tool_call"]["arguments"]["operation"] == "aggregate"


def test_supervisor_stops_at_loop_limit():
    state: WorkbenchState = {
        "user_query": "Read sample_equipment.csv and calculate average",
        "image_path": None,
        "pdf_path": None,
        "task_type": "DIRECT_CHAT",
        "plan": [],
        "vision_data": None,
        "rag_data": None,
        "steps_log": [],
        "citations": [],
        "final_answer": "",
        "status": "in_progress",
        "pending_tool_call": None,
        "tool_results": [{"tool_name": "dummy"}],
        "tool_call_count": 5,  # Max reached
        "max_tool_calls": 5,
    }

    result = supervisor_node(state)
    assert result["pending_tool_call"] is None
    next_node = route_decision({**state, **result})
    assert next_node == "synthesizer_node"


def test_tool_node_execution_and_step_logging():
    state: WorkbenchState = {
        "user_query": f"Read {SAMPLE_TXT}",
        "image_path": None,
        "pdf_path": None,
        "task_type": "DIRECT_CHAT",
        "plan": [],
        "vision_data": None,
        "rag_data": None,
        "steps_log": [{"step": 1, "agent": "Supervisor Agent", "action": "classified"}],
        "citations": [],
        "final_answer": "",
        "status": "in_progress",
        "pending_tool_call": {
            "tool_name": "file_reader",
            "arguments": {"file_path": SAMPLE_TXT},
        },
        "tool_results": [],
        "tool_call_count": 0,
        "max_tool_calls": 5,
    }

    output = tool_node(state)

    assert len(output["tool_results"]) == 1
    assert output["tool_call_count"] == 1
    assert output["pending_tool_call"] is None
    assert len(output["steps_log"]) == 2
    assert output["steps_log"][1]["agent"] == "Tool: File Reader"
    assert "sample_notes.txt" in output["steps_log"][1]["action"]


def test_b0_direct_chat_routing_preserved():
    state: WorkbenchState = {
        "user_query": "What is the capital of France?",
        "image_path": None,
        "pdf_path": None,
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

    sup_res = supervisor_node(state)
    assert sup_res["pending_tool_call"] is None
    assert sup_res["task_type"] == "DIRECT_CHAT"

    next_node = route_decision({**state, **sup_res})
    assert next_node == "synthesizer_node"


def test_b0_vision_routing_preserved():
    state: WorkbenchState = {
        "user_query": "Identify pump",
        "image_path": "drawing.png",
        "pdf_path": None,
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

    sup_res = supervisor_node(state)
    assert sup_res["pending_tool_call"] is None
    assert sup_res["task_type"] == "VISION_INSPECTION"

    next_node = route_decision({**state, **sup_res})
    assert next_node == "vision_node"


# ==============================================================================
# 7. ISSUE 1 & ISSUE 2 EXTENSION TESTS: THRESHOLD ROUTING & CSV UPLOAD
# ==============================================================================


def test_parse_threshold_query_patterns():
    # Test exceeding
    res1 = _parse_threshold_query(
        "identify every equipment item exceeding 5.0 mm/s vibration"
    )
    assert res1 == (">", 5.0, "vibration_mm_s")

    # Test above
    res2 = _parse_threshold_query("all pumps with temperature above 70")
    assert res2 == (">", 70.0, "temperature_c")

    # Test >
    res3 = _parse_threshold_query("equipment where vibration > 5.0")
    assert res3 == (">", 5.0, "vibration_mm_s")

    # Test >=
    res4 = _parse_threshold_query("pumps with vibration >= 5.8")
    assert res4 == (">=", 5.8, "vibration_mm_s")

    # Test below
    res5 = _parse_threshold_query("show records with temperature below 60")
    assert res5 == ("<", 60.0, "temperature_c")

    # Test less than
    res6 = _parse_threshold_query("equipment with operating hours less than 3000")
    assert res6 == ("<", 3000.0, "operating_hours")

    # Test <=
    res7 = _parse_threshold_query("temperature <= 55")
    assert res7 == ("<=", 55.0, "temperature_c")

    # Non-threshold queries return None
    assert _parse_threshold_query("top 5 equipment by vibration") is None
    assert _parse_threshold_query("summarize this document") is None


def test_parse_ranking_query_dynamic_k():
    # Explicit top 5
    res1 = _parse_ranking_query("what are the top 5 equipment by vibration?")
    assert res1 == (5, False, "vibration_mm_s")

    # Explicit top 10
    res2 = _parse_ranking_query("show the top 10 operating hours")
    assert res2 == (10, False, "operating_hours")

    # Lowest 2
    res3 = _parse_ranking_query("find the lowest 2 temperatures")
    assert res3 == (2, True, "temperature_c")

    # Default count (3) when K not explicitly provided
    res4 = _parse_ranking_query("highest vibration equipment")
    assert res4 == (3, False, "vibration_mm_s")

    # Non-ranking query
    assert (
        _parse_ranking_query(
            "identify every equipment item exceeding 5.0 mm/s vibration"
        )
        is None
    )


def test_supervisor_routes_threshold_filter_single_turn():
    state: WorkbenchState = {
        "user_query": f"Identify every equipment item exceeding 5.0 mm/s vibration in {SAMPLE_CSV}",
        "image_path": None,
        "pdf_path": None,
        "csv_path": None,
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

    result = supervisor_node(state)
    assert result["pending_tool_call"] is not None
    assert result["pending_tool_call"]["tool_name"] == "data_analysis"
    args = result["pending_tool_call"]["arguments"]
    assert args["operation"] == "filter"
    assert args["filter_column"] == "vibration_mm_s"
    assert args["filter_operator"] == ">"
    assert args["filter_value"] == 5.0


def test_supervisor_routes_threshold_filter_with_csv_path_state():
    # Simulates uploaded CSV attached to Workbench state (no filename in prompt!)
    state: WorkbenchState = {
        "user_query": "Identify every equipment item exceeding 5.0 mm/s vibration",
        "image_path": None,
        "pdf_path": None,
        "csv_path": SAMPLE_CSV,
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

    result = supervisor_node(state)
    assert result["pending_tool_call"] is not None
    assert result["pending_tool_call"]["tool_name"] == "data_analysis"
    args = result["pending_tool_call"]["arguments"]
    assert args["file_path"] == SAMPLE_CSV
    assert args["operation"] == "filter"
    assert args["filter_column"] == "vibration_mm_s"
    assert args["filter_operator"] == ">"
    assert args["filter_value"] == 5.0


def test_supervisor_routes_dynamic_top_k_with_csv_path_state():
    state: WorkbenchState = {
        "user_query": "What are the top 5 equipment by vibration?",
        "image_path": None,
        "pdf_path": None,
        "csv_path": SAMPLE_CSV,
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

    result = supervisor_node(state)
    assert result["pending_tool_call"] is not None
    assert result["pending_tool_call"]["tool_name"] == "data_analysis"
    args = result["pending_tool_call"]["arguments"]
    assert args["file_path"] == SAMPLE_CSV
    assert args["operation"] == "top_k"
    assert args["column"] == "vibration_mm_s"
    assert args["top_k_count"] == 5
    assert args["ascending"] is False


def test_supervisor_multi_tool_chaining_with_threshold_filter():
    file_result = {
        "success": True,
        "tool_name": "file_reader",
        "result": {
            "filename": "sample_equipment.csv",
            "file_type": "csv",
            "content": "equipment_id,category,vibration_mm_s...",
        },
        "metadata": {"resolved_path": SAMPLE_CSV},
    }

    state: WorkbenchState = {
        "user_query": "Read sample_equipment.csv and identify every equipment item exceeding 5.0 mm/s vibration.",
        "image_path": None,
        "pdf_path": None,
        "csv_path": None,
        "task_type": "DIRECT_CHAT",
        "plan": [],
        "vision_data": None,
        "rag_data": None,
        "steps_log": [{"step": 1, "agent": "Supervisor", "action": "start"}],
        "citations": [],
        "final_answer": "",
        "status": "in_progress",
        "pending_tool_call": None,
        "tool_results": [file_result],
        "tool_call_count": 1,
        "max_tool_calls": 5,
    }

    turn2_result = supervisor_node(state)
    assert turn2_result["pending_tool_call"] is not None
    assert turn2_result["pending_tool_call"]["tool_name"] == "data_analysis"
    args = turn2_result["pending_tool_call"]["arguments"]
    assert args["operation"] == "filter"
    assert args["filter_column"] == "vibration_mm_s"
    assert args["filter_operator"] == ">"
    assert args["filter_value"] == 5.0


def test_data_analysis_filter_returns_all_matching_records():
    tool = DataAnalysisTool()
    res = tool.execute(
        file_path=SAMPLE_CSV,
        operation="filter",
        filter_column="vibration_mm_s",
        filter_operator=">",
        filter_value=5.0,
    )

    assert res.success is True
    assert res.result["operation"] == "filter"
    analysis = res.result["analysis"]
    assert analysis["matching_count"] == 2
    matched_ids = [r["equipment_id"] for r in analysis["rows_preview"]]
    assert "P-102" in matched_ids
    assert "C-202" in matched_ids


def test_non_tool_query_without_file_does_not_route_to_data_analysis():
    state: WorkbenchState = {
        "user_query": "Why does pressure increase above 100 bar during thermal expansion?",
        "image_path": None,
        "pdf_path": None,
        "csv_path": None,
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

    result = supervisor_node(state)
    # Should route to SOP_QUERY or DIRECT_CHAT, NOT data_analysis tool
    if result["pending_tool_call"] is not None:
        assert result["pending_tool_call"]["tool_name"] != "data_analysis"


# ==============================================================================
# 8. SUPERVISOR CONTROLLED PYTHON ROUTING TESTS
# ==============================================================================


def test_supervisor_routes_to_python_calculate_math():
    state: WorkbenchState = {
        "user_query": "Use Python to calculate 25 / 1.5 * 0.88.",
        "image_path": None,
        "pdf_path": None,
        "csv_path": None,
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
    result = supervisor_node(state)
    assert result["pending_tool_call"] is not None
    assert result["pending_tool_call"]["tool_name"] == "python_execute"
    assert "25 / 1.5 * 0.88" in result["pending_tool_call"]["arguments"]["code"]


def test_supervisor_routes_to_python_safe_operating_pressure():
    state: WorkbenchState = {
        "user_query": (
            "Calculate the safe operating pressure limit when the design pressure is 25 bar, "
            "safety factor is 1.5, and temperature derating is 0.88 using Python."
        ),
        "image_path": None,
        "pdf_path": None,
        "csv_path": None,
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
    result = supervisor_node(state)
    assert result["pending_tool_call"] is not None
    assert result["pending_tool_call"]["tool_name"] == "python_execute"
    code = result["pending_tool_call"]["arguments"]["code"]
    assert "p_design = 25.0" in code
    assert "safety_factor = 1.5" in code
    assert "temperature_derating = 0.88" in code


def test_supervisor_routes_to_python_unsafe_import_os():
    state: WorkbenchState = {
        "user_query": "Use Python to import os and list the files in the current directory.",
        "image_path": None,
        "pdf_path": None,
        "csv_path": None,
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
    result = supervisor_node(state)
    assert result["pending_tool_call"] is not None
    assert result["pending_tool_call"]["tool_name"] == "python_execute"
    assert "import os" in result["pending_tool_call"]["arguments"]["code"]

    # Verify that when tool_node executes this pending call, the security boundary rejects it
    tool_output = tool_node({**state, **result})
    assert len(tool_output["tool_results"]) == 1
    tr = tool_output["tool_results"][0]
    assert tr["success"] is False
    assert tr["error"]["code"] == "SECURITY_VIOLATION"
    assert "os" in tr["error"]["message"]


def test_supervisor_preserves_sop_query_routing():
    state: WorkbenchState = {
        "user_query": "Search the SOP for the safe operating pressure limit.",
        "image_path": None,
        "pdf_path": None,
        "csv_path": None,
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
    result = supervisor_node(state)
    assert result["pending_tool_call"] is None
    assert result["task_type"] == "SOP_QUERY"


def test_supervisor_preserves_explain_operating_pressure():
    state: WorkbenchState = {
        "user_query": "Explain operating pressure.",
        "image_path": None,
        "pdf_path": None,
        "csv_path": None,
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
    result = supervisor_node(state)
    assert result["pending_tool_call"] is None
    assert result["task_type"] in ["SOP_QUERY", "DIRECT_CHAT"]


def test_supervisor_preserves_explain_what_python_is():
    state: WorkbenchState = {
        "user_query": "Explain what Python is.",
        "image_path": None,
        "pdf_path": None,
        "csv_path": None,
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
    result = supervisor_node(state)
    assert result["pending_tool_call"] is None
    assert result["task_type"] == "DIRECT_CHAT"
