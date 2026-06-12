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
    sentence_grounding_node,
    confidence_node,
)


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

    Akis (v4 — critic kaldirildi):
    scope_check -> (in_scope) -> compress -> retriever -> generator
                                                              |
                                                              v
                                                    sentence_grounding (LettuceDetect)
                                                              |
                                                              v
                                                         confidence -> END
                -> (out_of_scope) -> confidence -> END

    Notlar:
      - Critic v4'te tamamen kaldirildi. Onceki rolleri:
        * `grounded`        -> sentence_grounding (LettuceDetect) yapiyor
        * `answer_relevant` -> retrieval rerank skoru zaten gosteriyor
        * `disclaimer`      -> generator prompt'unda hard rule
        * `emergency`       -> generator prompt'unda hard rule
        * `lay_language`    -> generator prompt'unda hard rule (producer)
      - Retry dongusu yok artik. Generator tek seferde uretir, grounding temizler.
    """
    graph = StateGraph(AgentState)

    # Node'lari ekle
    graph.add_node("scope_check", scope_check_node)
    graph.add_node("compress", compress_node)
    graph.add_node("retriever", retriever_node)
    graph.add_node("generator", generator_node)
    graph.add_node("sentence_grounding", sentence_grounding_node)
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

    # Generator -> Sentence Grounding (LettuceDetect) -> Confidence
    # Critic kaldirildi: LettuceDetect token-level grounding'i tek basina yapiyor.
    graph.add_edge("generator", "sentence_grounding")
    graph.add_edge("sentence_grounding", "confidence")

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
