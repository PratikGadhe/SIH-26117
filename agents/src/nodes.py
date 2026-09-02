"""
LangGraph Worker Nodes for SIH 26117 Agents
Implements Supervisor (Planner), Vision, RAG, and Synthesizer nodes.
"""

import os
import sys
import time
from typing import Dict, Any, List

current_dir = os.path.dirname(os.path.abspath(__file__))
agents_root = os.path.abspath(os.path.join(current_dir, ".."))
if agents_root not in sys.path:
    sys.path.insert(0, agents_root)

from src.state import WorkbenchState
from src.ollama_text_client import OllamaTextClient
from src.prompts import SUPERVISOR_SYSTEM_PROMPT, SYNTHESIZER_SYSTEM_PROMPT
from vision_tool import vision_tool, pdf_tool
from rag_tool import rag_tool

# Initialize local Qwen reasoning model
llm_client = OllamaTextClient(base_url="http://localhost:11434", model_name="qwen3:4b")


def supervisor_node(state: WorkbenchState) -> Dict[str, Any]:
    """
    Analyzes the user query and inputs, classifies task type, and builds execution plan.
    """
    user_query = state.get("user_query", "")
    image_path = state.get("image_path")
    pdf_path = state.get("pdf_path")

    # Fast deterministic classification to prevent LLM latency overhead
    if image_path or pdf_path:
        if any(w in user_query.lower() for w in ["sop", "safety", "rule", "limit", "allow", "comply", "violate", "standard"]):
            task_type = "HYBRID_AUDIT"
            plan = ["Inspect visual schematic with Qwen3-VL", "Retrieve matching SOP rules from ChromaDB", "Audit compliance with Qwen3 4B"]
        else:
            task_type = "VISION_INSPECTION"
            plan = ["Analyze visual schematic with Qwen3-VL", "Summarize detected components and status"]
    elif any(w in user_query.lower() for w in ["sop", "manual", "rule", "limit", "pressure", "temperature", "procedure", "shutdown", "startup"]):
        task_type = "SOP_QUERY"
        plan = ["Search refinery knowledge base via ChromaDB", "Synthesize safety advice with Qwen3 4B"]
    else:
        task_type = "DIRECT_CHAT"
        plan = ["Process general engineering query with Qwen3 4B"]

    step_entry = {
        "step": 1,
        "agent": "Supervisor Agent",
        "action": f"Classified task as {task_type}",
        "plan": plan
    }

    return {
        "task_type": task_type,
        "plan": plan,
        "steps_log": state.get("steps_log", []) + [step_entry]
    }


def vision_node(state: WorkbenchState) -> Dict[str, Any]:
    """
    Executes Member 4's Vision Tool on uploaded P&ID diagrams or PDFs.
    """
    image_path = state.get("image_path")
    pdf_path = state.get("pdf_path")
    user_query = state.get("user_query", "")

    vision_result = {}
    if image_path and os.path.exists(image_path):
        vision_result = vision_tool(image_path, user_query)
    elif pdf_path and os.path.exists(pdf_path):
        vision_result = pdf_tool(pdf_path, user_query)
    else:
        vision_result = {"status": "skipped", "message": "No valid image/PDF file provided"}

    step_entry = {
        "step": len(state.get("steps_log", [])) + 1,
        "agent": "Vision Agent (Qwen3-VL)",
        "action": f"Inspected visual asset: {image_path or pdf_path}",
        "findings_summary": vision_result.get("analysis", "")[:200] + "..." if vision_result.get("analysis") else "Done"
    }

    return {
        "vision_data": vision_result,
        "steps_log": state.get("steps_log", []) + [step_entry]
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
        citations.append({
            "source": item.get("source", "MRPL Manual"),
            "page": item.get("page", "N/A"),
            "distance": item.get("distance", 0.0)
        })

    step_entry = {
        "step": len(state.get("steps_log", [])) + 1,
        "agent": "RAG Knowledge Agent (ChromaDB)",
        "action": f"Queried SOP knowledge base with: '{user_query}'",
        "sources_retrieved": len(citations)
    }

    return {
        "rag_data": rag_result,
        "citations": citations,
        "steps_log": state.get("steps_log", []) + [step_entry]
    }


def synthesizer_node(state: WorkbenchState) -> Dict[str, Any]:
    """
    Combines vision analysis and RAG manual excerpts into a formal report.
    """
    user_query = state.get("user_query", "")
    task_type = state.get("task_type", "DIRECT_CHAT")
    vision_data = state.get("vision_data") or {}
    rag_data = state.get("rag_data") or {}

    context_parts = []

    if vision_data.get("analysis"):
        context_parts.append(f"### Visual Inspection Findings (Qwen3-VL):\n{vision_data['analysis']}")

    if rag_data.get("context"):
        context_parts.append(f"### Relevant MRPL SOP Knowledge Base Excerpts:\n{rag_data['context']}")

    combined_context = "\n\n".join(context_parts) if context_parts else "No external documents or visual assets referenced."

    synthesis_prompt = f"""User Question:
{user_query}

Verified Context & Evidence Gathered:
{combined_context}

Provide a structured, authoritative engineering assessment as the Chief Safety Lead."""

    report_res = llm_client.generate(
        prompt=synthesis_prompt,
        system_prompt=SYNTHESIZER_SYSTEM_PROMPT,
        temperature=0.2
    )

    final_text = report_res.get("response", "Report generation failed.")

    step_entry = {
        "step": len(state.get("steps_log", [])) + 1,
        "agent": "Synthesis Agent (Qwen3 4B)",
        "action": "Generated final verified compliance report"
    }

    return {
        "final_answer": final_text,
        "steps_log": state.get("steps_log", []) + [step_entry],
        "status": "success"
    }
