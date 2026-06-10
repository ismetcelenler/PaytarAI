"""
PaytarAI — LangGraph Workflow Compilation

Node'lari birlestirip graph'i derler.
AI-PROMPT.md Section 4: Compress -> Retriever -> Generator <-> Critic -> Confidence
"""

from langgraph.graph import StateGraph, END

from app.graph.state import AgentState
from app.graph.nodes import (
    scope_check_node,
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


def after_scope_check(state: dict) -> str:
    """
    Scope check sonrasi yonlendirme.
    - out_of_scope -> direkt confidence'a atla (retriever/generator/critic atlanir)
    - in_scope -> normal akis (compress -> retriever -> ...)
    """
    if state.get("response_status") == "out_of_scope":
        return "confidence"
    return "compress"


# Confidence gate'in retriever'dan sonra erken karar verme esigi.
# confidence_node icindeki INSUFFICIENT_THRESHOLD ile ayni tutulmali.
EARLY_CONFIDENCE_THRESHOLD = 0.60


def after_retriever(state: dict) -> str:
    """
    Retriever sonrasi yonlendirme.
    - top_sim < EARLY_CONFIDENCE_THRESHOLD ise generator'i ATLA, dogrudan confidence'a
      git (confidence node template fallback dondurur). 50+ saniyelik LLM cagrisini
      bosa harcamayalim.
    - Aksi halde normal generator akisi.
    """
    top_sim = state.get("retrieval_similarity_score", 0.0)
    if top_sim < EARLY_CONFIDENCE_THRESHOLD:
        return "confidence"  # generator atla, confidence template fallback yapar
    return "generator"


def build_graph() -> StateGraph:
    """
    LangGraph workflow'u olusturur ve derler.

    Akis:
    scope_check -> (in_scope) -> compress -> retriever -> generator -> critic
                                                                          |
                                                            rejected -> generator (max 2 kez)
                                                            accepted -> confidence -> END
                -> (out_of_scope) -> confidence -> END
    """
    graph = StateGraph(AgentState)

    # Node'lari ekle
    graph.add_node("scope_check", scope_check_node)
    graph.add_node("compress", compress_node)
    graph.add_node("retriever", retriever_node)
    graph.add_node("generator", generator_node)
    graph.add_node("critic", critic_node)
    graph.add_node("confidence", confidence_node)

    # Entry point: scope_check
    graph.set_entry_point("scope_check")

    # Conditional edge: scope_check -> compress (in-scope) veya confidence (out-of-scope)
    graph.add_conditional_edges(
        "scope_check",
        after_scope_check,
        {
            "compress": "compress",
            "confidence": "confidence",
        },
    )

    # Normal akis (in-scope sorular icin)
    graph.add_edge("compress", "retriever")

    # Retriever sonrasi early confidence gate:
    # top_sim cok dususe generator'i atla, direkt confidence'a git (template fallback).
    graph.add_conditional_edges(
        "retriever",
        after_retriever,
        {
            "generator": "generator",
            "confidence": "confidence",
        },
    )
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
