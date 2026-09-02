"""
LangGraph State Definition for SIH 26117 Workbench
The shared memory clipboard across all nodes in the agent graph.
"""

from typing import TypedDict, List, Dict, Any, Optional


class WorkbenchState(TypedDict):
    """
    Shared state clipboard passed between LangGraph nodes.
    """
    user_query: str                          # Original user prompt
    image_path: Optional[str]                # Path to P&ID diagram / drawing (if any)
    pdf_path: Optional[str]                  # Path to uploaded PDF document (if any)
    task_type: str                           # Classified intent: HYBRID_AUDIT, VISION_INSPECTION, SOP_QUERY, DIRECT_CHAT
    plan: List[str]                          # Step-by-step execution plan
    vision_data: Optional[Dict[str, Any]]    # Results from Member 4 (Qwen3-VL Vision tool)
    rag_data: Optional[Dict[str, Any]]       # Results from Member 2 (ChromaDB RAG tool)
    steps_log: List[Dict[str, Any]]          # Audit trail of executed steps for React UI
    citations: List[Dict[str, Any]]          # Specific document/page citations
    final_answer: str                        # Final synthesized engineering report
    status: str                              # "success" or "error"
