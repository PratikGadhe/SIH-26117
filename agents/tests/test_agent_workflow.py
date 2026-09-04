"""
Integration Test Suite: LangGraph Multi-Agent Workflow
Tests end-to-end routing, vision tool execution, RAG search, and report synthesis.
"""

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from agents.agent_service import run_agentic_workflow


def test_pure_sop_query():
    print("=" * 65, flush=True)
    print("TEST 1: Pure SOP / Safety Manual Query", flush=True)
    print("=" * 65, flush=True)

    query = "What is the procedure for emergency shutdown of a distillation column?"
    print(f"Query: \"{query}\"\n", flush=True)

    result = run_agentic_workflow(user_query=query)

    print("📊 RESULT STATUS:", result["status"], flush=True)
    print("🏷️ TASK TYPE    :", result["task_type"], flush=True)
    print("⏱️ TIME TAKEN   :", result["execution_time_seconds"], "seconds\n", flush=True)
    print("📝 STEPS TAKEN:", flush=True)
    for s in result["steps_taken"]:
        print(f"   • Step {s['step']}: {s['agent']} -> {s['action']}", flush=True)

    print("\n🤖 FINAL REPORT:\n", result["final_answer"], flush=True)
    assert result["status"] == "success"
    assert len(result["steps_taken"]) >= 2


def test_hybrid_diagram_audit():
    print("\n" + "=" * 65, flush=True)
    print("TEST 2: Hybrid Visual Diagram + Safety Audit", flush=True)
    print("=" * 65, flush=True)

    sample_img = os.path.join(project_root, "vision", "tests", "sample_images", "test_diagram.png")
    query = "Inspect this schematic. What components are visible, and is the pump labeled correctly?"

    print(f"Image: {sample_img}", flush=True)
    print(f"Query: \"{query}\"\n", flush=True)

    result = run_agentic_workflow(user_query=query, image_path=sample_img)

    print("📊 RESULT STATUS:", result["status"], flush=True)
    print("🏷️ TASK TYPE    :", result["task_type"], flush=True)
    print("⏱️ TIME TAKEN   :", result["execution_time_seconds"], "seconds\n", flush=True)
    print("📝 STEPS TAKEN:", flush=True)
    for s in result["steps_taken"]:
        print(f"   • Step {s['step']}: {s['agent']} -> {s['action']}", flush=True)

    print("\n🤖 FINAL REPORT:\n", result["final_answer"], flush=True)
    assert result["status"] == "success"
    assert len(result["steps_taken"]) >= 3


if __name__ == "__main__":
    test_pure_sop_query()
    test_hybrid_diagram_audit()
    print("\n🎉 ALL LANGGRAPH INTEGRATION TESTS PASSED SUCCESSFULLY!", flush=True)
