"""
LangGraph Workflow Assembly for SIH 26117 Agents
Compiles StateGraph with dynamic conditional branching.
"""

from langgraph.graph import StateGraph, START, END
from src.state import WorkbenchState
from src.nodes import supervisor_node, vision_node, rag_node, synthesizer_node


def route_decision(state: WorkbenchState) -> str:
    """
    Determines next node based on Supervisor's task classification.
    """
    task_type = state.get("task_type", "DIRECT_CHAT")

    if task_type in ["HYBRID_AUDIT", "VISION_INSPECTION"]:
        return "vision_node"
    elif task_type == "SOP_QUERY":
        return "rag_node"
    else:
        return "synthesizer_node"


def route_after_vision(state: WorkbenchState) -> str:
    """
    After vision inspection, decides whether to cross-reference RAG or go straight to synthesis.
    """
    task_type = state.get("task_type", "VISION_INSPECTION")
    if task_type == "HYBRID_AUDIT":
        return "rag_node"
    return "synthesizer_node"


def create_agent_graph():
    """
    Builds and compiles the master LangGraph workflow.
    """
    workflow = StateGraph(WorkbenchState)

    # 1. Add Nodes
    workflow.add_node("supervisor_node", supervisor_node)
    workflow.add_node("vision_node", vision_node)
    workflow.add_node("rag_node", rag_node)
    workflow.add_node("synthesizer_node", synthesizer_node)

    # 2. Add Edges & Conditional Routes
    workflow.add_edge(START, "supervisor_node")

    workflow.add_conditional_edges(
        "supervisor_node",
        route_decision,
        {
            "vision_node": "vision_node",
            "rag_node": "rag_node",
            "synthesizer_node": "synthesizer_node"
        }
    )

    workflow.add_conditional_edges(
        "vision_node",
        route_after_vision,
        {
            "rag_node": "rag_node",
            "synthesizer_node": "synthesizer_node"
        }
    )

    workflow.add_edge("rag_node", "synthesizer_node")
    workflow.add_edge("synthesizer_node", END)

    return workflow.compile()


# Singleton compiled graph
agent_graph = create_agent_graph()
