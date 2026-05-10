"""
PaytarAI — LangGraph Workflow Compilation

Node'lari birlestirip graph'i derler.
AI-PROMPT.md Section 4: Compress -> Retriever -> Generator <-> Critic -> Confidence
"""

from langgraph.graph import StateGraph, END

from app.graph.state import AgentState
from app.graph.nodes import (
    compress_node,
    retriever_node,
    generator_node,
    critic_node,
    confidence_node,
)


def should_retry(state: dict) -> str:
    """
    Critic sonucuna gore yonlendirme.
    - rejected -> generator'a geri don
    - accepted / accepted_after_max_retries -> confidence'a git
    """
    status = state.get("response_status", "")

    if status == "rejected":
        return "generator"
    return "confidence"


def build_graph() -> StateGraph:
    """
    LangGraph workflow'u olusturur ve derler.

    Akis:
    compress -> retriever -> generator -> critic
                                            |
                              rejected -> generator (max 2 kez)
                              accepted -> confidence -> END
    """
    graph = StateGraph(AgentState)

    # Node'lari ekle
    graph.add_node("compress", compress_node)
    graph.add_node("retriever", retriever_node)
    graph.add_node("generator", generator_node)
    graph.add_node("critic", critic_node)
    graph.add_node("confidence", confidence_node)

    # Kenarlar
    graph.set_entry_point("compress")
    graph.add_edge("compress", "retriever")
    graph.add_edge("retriever", "generator")
    graph.add_edge("generator", "critic")

    # Conditional edge: critic -> generator (retry) veya confidence (accept)
    graph.add_conditional_edges(
        "critic",
        should_retry,
        {
            "generator": "generator",
            "confidence": "confidence",
        },
    )

    graph.add_edge("confidence", END)

    return graph.compile()


# Singleton compiled graph
_workflow = None


def get_workflow():
    """Compiled workflow singleton."""
    global _workflow
    if _workflow is None:
        _workflow = build_graph()
    return _workflow
