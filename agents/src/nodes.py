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
from src.prompts import (
    SUPERVISOR_SYSTEM_PROMPT,
    SYNTHESIZER_SYSTEM_PROMPT,
    DOCUMENT_QA_SYNTHESIZER_PROMPT,
    IMAGE_SYNTHESIZER_PROMPT,
    DIRECT_CHAT_SYNTHESIZER_PROMPT,
)
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
    if pdf_path:
        task_type = "VISION_INSPECTION"
        plan = [
            "Extract document text and structure via PyMuPDF",
            "Synthesize document findings with Qwen3 4B",
        ]
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
    else:
        task_type = "DIRECT_CHAT"
        plan = ["Process general engineering query with Qwen3 4B"]

    step_entry = {
        "step": 1,
        "agent": "Supervisor Agent",
        "action": f"Classified task as {task_type}",
        "plan": plan,
    }

    return {
        "task_type": task_type,
        "plan": plan,
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


def synthesizer_node(state: WorkbenchState) -> Dict[str, Any]:
    """
    Combines vision analysis and RAG manual excerpts into a grounded document, visual, or formal report answer.
    """
    user_query = state.get("user_query", "")
    task_type = state.get("task_type", "DIRECT_CHAT")
    image_path = state.get("image_path")
    pdf_path = state.get("pdf_path")
    vision_data = state.get("vision_data") or {}
    rag_data = state.get("rag_data") or {}

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
