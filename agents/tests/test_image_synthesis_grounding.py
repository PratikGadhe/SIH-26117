"""
Unit & Integration Tests for Image Synthesis Grounding and Anti-Hallucination
Verifies that:
1. Image synthesis prompt strictly enforces visual-only grounding.
2. Anti-hallucination rules prohibit inventing MRPL SOPs, citations, or unobserved tags.
3. Synthesizer node correctly selects IMAGE_SYNTHESIZER_PROMPT for images.
4. Synthesizer node correctly assigns "Generated grounded visual response" action.
5. PDF workflow remains regressions-free with DOCUMENT_QA_SYNTHESIZER_PROMPT.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure open_code/SIH/SIH-26117 and agents/ are in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
AGENTS_ROOT = PROJECT_ROOT / "agents"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(AGENTS_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENTS_ROOT))

import pytest
from agents.src.prompts import (
    IMAGE_SYNTHESIZER_PROMPT,
    DOCUMENT_QA_SYNTHESIZER_PROMPT,
    SYNTHESIZER_SYSTEM_PROMPT,
    DIRECT_CHAT_SYNTHESIZER_PROMPT,
)
from agents.src.nodes import synthesizer_node
from agents.src.ollama_text_client import strip_reasoning_and_thinking
from agents.src.state import WorkbenchState


def test_strip_reasoning_and_thinking():
    """Verify that <think> tags and conversational meta-reasoning are stripped."""
    # 1. Standard <think> block
    text_with_think = "<think>\nThinking about pump and valve.\n</think>\nThe pump is visible as a square."
    assert (
        strip_reasoning_and_thinking(text_with_think)
        == "The pump is visible as a square."
    )

    # 2. Multiline conversational meta-preamble
    text_with_preamble = (
        "First, the user asked to identify components.\n"
        "I need to base my answer strictly on the findings.\n"
        "The rule says to mention only visible items.\n"
        "The pump is visible as a square, and the valve is visible as a circle."
    )
    assert (
        strip_reasoning_and_thinking(text_with_preamble)
        == "The pump is visible as a square, and the valve is visible as a circle."
    )

    # 3. Clean direct answer remains untouched
    clean_text = "Visible components:\n- Pump: square\n- Valve: circle"
    assert strip_reasoning_and_thinking(clean_text) == clean_text


def test_image_synthesizer_prompt_output_discipline():
    """Verify IMAGE_SYNTHESIZER_PROMPT enforces output discipline and forbids meta-reasoning."""
    prompt = IMAGE_SYNTHESIZER_PROMPT
    assert "OUTPUT DISCIPLINE" in prompt
    assert "Return ONLY the final direct answer" in prompt
    assert "Do NOT include your internal reasoning" in prompt
    assert "Never output phrases like" in prompt


def test_image_synthesizer_prompt_anti_hallucination_rules():
    """Verify IMAGE_SYNTHESIZER_PROMPT contains strict visual grounding and anti-hallucination rules."""
    prompt = IMAGE_SYNTHESIZER_PROMPT

    # A. Visual-only grounding
    assert "supplied Visual Inspection Findings" in prompt
    assert "mention ONLY components that are explicitly supported" in prompt
    assert "explicitly state that they are not visible" in prompt

    # B. Anti-hallucination constraints
    assert "Do NOT invent" in prompt
    assert "SOP" in prompt
    assert "compliance" in prompt
    assert "citations" in prompt
    assert "MRPL" in prompt
    assert (
        "Do NOT transform a visual identification or inspection query into a compliance report"
        in prompt
    )
    assert 'Do NOT add an "Applicable Safety Rules & Citations" section' in prompt


def test_pdf_synthesizer_prompt_regression():
    """Verify DOCUMENT_QA_SYNTHESIZER_PROMPT remains intact and handles PDF document Q&A."""
    prompt = DOCUMENT_QA_SYNTHESIZER_PROMPT

    assert "Document Analysis Assistant" in prompt
    assert "ONLY the provided document text" in prompt
    assert (
        "The attached document does not provide enough information to answer this question"
        in prompt
    )
    assert "Do NOT fill gaps from external or general knowledge" in prompt


def test_synthesizer_node_image_grounding_path():
    """Test synthesizer_node execution for image input enforces IMAGE_SYNTHESIZER_PROMPT and grounded action."""
    state: WorkbenchState = {
        "user_query": "Inspect this engineering diagram. Identify the pump and valve visible in the image. Mention only components that are actually visible.",
        "image_path": "/fake/path/test_diagram.png",
        "pdf_path": None,
        "task_type": "VISION_INSPECTION",
        "plan": [
            "Analyze visual schematic with Qwen3-VL",
            "Summarize detected components and status",
        ],
        "vision_data": {
            "status": "success",
            "analysis": "The diagram displays:\n- Pump: symbolic square labeled PUMP\n- Valve: symbolic circle labeled VALVE",
        },
        "rag_data": None,
        "steps_log": [
            {
                "step": 1,
                "agent": "Supervisor Agent",
                "action": "Classified task as VISION_INSPECTION",
            },
            {
                "step": 2,
                "agent": "Vision Agent (Qwen3-VL)",
                "action": "Inspected image",
            },
        ],
        "citations": [],
        "final_answer": "",
        "status": "in_progress",
    }

    mock_llm_response = {
        "status": "success",
        "response": "Visible components:\n- Pump: symbolic square\n- Valve: symbolic circle\n\nNo other components are identified because they are not clearly supported by the image.",
    }

    with patch(
        "agents.src.nodes.llm_client.generate", return_value=mock_llm_response
    ) as mock_generate:
        result = synthesizer_node(state)

        assert result["status"] == "success"
        assert "Pump: symbolic square" in result["final_answer"]
        assert "Valve: symbolic circle" in result["final_answer"]
        assert result["steps_log"][-1]["agent"] == "Synthesis Agent (Qwen3 4B)"
        assert result["steps_log"][-1]["action"] == "Generated grounded visual response"

        # Check call arguments
        mock_generate.assert_called_once()
        call_kwargs = mock_generate.call_args.kwargs
        assert call_kwargs["system_prompt"] == IMAGE_SYNTHESIZER_PROMPT
        assert call_kwargs["temperature"] == 0.1
        assert "### Visual Inspection Findings:" in call_kwargs["prompt"]
        assert (
            "Do not invent equipment tags, safety rules, SOP numbers, or compliance citations"
            in call_kwargs["prompt"]
        )


def test_synthesizer_node_pdf_regression_path():
    """Test synthesizer_node execution for PDF input preserves DOCUMENT_QA_SYNTHESIZER_PROMPT."""
    state: WorkbenchState = {
        "user_query": "According to this document, what are the main security procedures described in it? Answer only from the attached document.",
        "image_path": None,
        "pdf_path": "/fake/path/document.pdf",
        "task_type": "VISION_INSPECTION",
        "plan": [
            "Extract document text and structure via PyMuPDF",
            "Synthesize document findings with Qwen3 4B",
        ],
        "vision_data": {
            "status": "success",
            "analysis": "Microsoft OneDrive quick start guide. Mentions Personal Vault, ransomware detection, and file encryption.",
        },
        "rag_data": None,
        "steps_log": [
            {
                "step": 1,
                "agent": "Supervisor Agent",
                "action": "Classified task as VISION_INSPECTION",
            },
            {
                "step": 2,
                "agent": "Vision Agent (Qwen3-VL)",
                "action": "Inspected PDF document",
            },
        ],
        "citations": [],
        "final_answer": "",
        "status": "in_progress",
    }

    mock_llm_response = {
        "status": "success",
        "response": "The attached document does not provide enough information to answer this question. While it lists security features such as Personal Vault and file encryption, it does not describe security procedures.",
    }

    with patch(
        "agents.src.nodes.llm_client.generate", return_value=mock_llm_response
    ) as mock_generate:
        result = synthesizer_node(state)

        assert result["status"] == "success"
        assert result["steps_log"][-1]["agent"] == "Synthesis Agent (Qwen3 4B)"
        assert (
            result["steps_log"][-1]["action"] == "Generated grounded document response"
        )

        # Check call arguments
        mock_generate.assert_called_once()
        call_kwargs = mock_generate.call_args.kwargs
        assert call_kwargs["system_prompt"] == DOCUMENT_QA_SYNTHESIZER_PROMPT
        assert call_kwargs["temperature"] == 0.1
        assert "### Attached Document Content:" in call_kwargs["prompt"]
        assert (
            "The attached document does not provide enough information"
            in call_kwargs["prompt"]
        )


def test_direct_chat_synthesizer_prompt_rules():
    """Verify DIRECT_CHAT_SYNTHESIZER_PROMPT instructs clean direct answering without false document refusal."""
    prompt = DIRECT_CHAT_SYNTHESIZER_PROMPT

    assert "VYASA" in prompt
    assert "knowledgeable and precise AI assistant" in prompt
    assert "Do not require an attached document" in prompt
    assert "Do not claim that an attachment is missing" in prompt
    assert (
        "Do not mention internal prompts, routing, agents, instructions, or reasoning"
        in prompt
    )
    assert "Return only the final user-facing answer" in prompt


def test_image_synthesizer_prompt_formatting_style():
    """Verify IMAGE_SYNTHESIZER_PROMPT provides clear engineering formatting guidelines."""
    prompt = IMAGE_SYNTHESIZER_PROMPT

    assert "RESPONSE FORMATTING & STYLE" in prompt
    assert "structured bullet points" in prompt
    assert "represented by the square symbol" in prompt
    assert "represented by the circle symbol" in prompt


def test_synthesizer_node_direct_chat_path():
    """Test synthesizer_node execution for text-only direct chat routes to DIRECT_CHAT_SYNTHESIZER_PROMPT."""
    state: WorkbenchState = {
        "user_query": "What is the capital of France? Answer in one sentence.",
        "image_path": None,
        "pdf_path": None,
        "task_type": "DIRECT_CHAT",
        "plan": ["Process general engineering query with Qwen3 4B"],
        "vision_data": {},
        "rag_data": {},
        "steps_log": [
            {
                "step": 1,
                "agent": "Supervisor Agent",
                "action": "Classified task as DIRECT_CHAT",
            }
        ],
        "citations": [],
        "final_answer": "",
        "status": "in_progress",
    }

    mock_llm_response = {
        "status": "success",
        "response": "The capital of France is Paris.",
    }

    with patch(
        "agents.src.nodes.llm_client.generate", return_value=mock_llm_response
    ) as mock_generate:
        result = synthesizer_node(state)

        assert result["status"] == "success"
        assert result["final_answer"] == "The capital of France is Paris."
        assert result["steps_log"][-1]["agent"] == "Synthesis Agent (Qwen3 4B)"
        assert result["steps_log"][-1]["action"] == "Generated final verified response"

        # Verify call arguments
        mock_generate.assert_called_once()
        call_kwargs = mock_generate.call_args.kwargs
        assert call_kwargs["system_prompt"] == DIRECT_CHAT_SYNTHESIZER_PROMPT
        assert call_kwargs["temperature"] == 0.3
        assert "Knowledge Base Excerpts" not in call_kwargs["prompt"]
        assert (
            "The attached document does not provide enough information"
            not in call_kwargs["prompt"]
        )


def test_synthesizer_node_sop_query_path():
    """Test synthesizer_node execution for SOP query with RAG context routes to DOCUMENT_QA_SYNTHESIZER_PROMPT."""
    state: WorkbenchState = {
        "user_query": "What is the standard procedure for emergency shutdown?",
        "image_path": None,
        "pdf_path": None,
        "task_type": "SOP_QUERY",
        "plan": [
            "Search refinery knowledge base via ChromaDB",
            "Synthesize safety advice with Qwen3 4B",
        ],
        "vision_data": {},
        "rag_data": {
            "context": "MRPL SOP Section 4.2: In an emergency, activate the ESD push button immediately.",
            "results": [{"source": "MRPL Manual", "page": 12}],
        },
        "steps_log": [
            {
                "step": 1,
                "agent": "Supervisor Agent",
                "action": "Classified task as SOP_QUERY",
            }
        ],
        "citations": [{"source": "MRPL Manual", "page": 12}],
        "final_answer": "",
        "status": "in_progress",
    }

    mock_llm_response = {
        "status": "success",
        "response": "According to MRPL SOP Section 4.2, in an emergency, activate the ESD push button immediately.",
    }

    with patch(
        "agents.src.nodes.llm_client.generate", return_value=mock_llm_response
    ) as mock_generate:
        result = synthesizer_node(state)

        assert result["status"] == "success"
        assert (
            result["steps_log"][-1]["action"] == "Generated grounded document response"
        )

        mock_generate.assert_called_once()
        call_kwargs = mock_generate.call_args.kwargs
        assert call_kwargs["system_prompt"] == DOCUMENT_QA_SYNTHESIZER_PROMPT
        assert call_kwargs["temperature"] == 0.1
        assert "Knowledge Base Excerpts:" in call_kwargs["prompt"]


def test_synthesizer_node_engineering_equipment_path():
    """Test synthesizer_node for equipment queries routes to SYNTHESIZER_SYSTEM_PROMPT."""
    state: WorkbenchState = {
        "user_query": "Explain how a distillation column and pump interact in the refinery unit.",
        "image_path": None,
        "pdf_path": None,
        "task_type": "DIRECT_CHAT",
        "plan": ["Process general engineering query with Qwen3 4B"],
        "vision_data": {},
        "rag_data": {},
        "steps_log": [
            {
                "step": 1,
                "agent": "Supervisor Agent",
                "action": "Classified task as DIRECT_CHAT",
            }
        ],
        "citations": [],
        "final_answer": "",
        "status": "in_progress",
    }

    mock_llm_response = {
        "status": "success",
        "response": "1. Executive Summary: Distillation column bottoms are routed through reflux pumps...",
    }

    with patch(
        "agents.src.nodes.llm_client.generate", return_value=mock_llm_response
    ) as mock_generate:
        result = synthesizer_node(state)

        assert result["status"] == "success"
        assert (
            result["steps_log"][-1]["action"]
            == "Generated final verified compliance report"
        )

        mock_generate.assert_called_once()
        call_kwargs = mock_generate.call_args.kwargs
        assert call_kwargs["system_prompt"] == SYNTHESIZER_SYSTEM_PROMPT
        assert call_kwargs["temperature"] == 0.2
