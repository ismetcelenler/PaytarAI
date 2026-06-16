"""
PaytarAI — LangGraph Workflow Compilation

Node'lari birlestirip graph'i derler.

v6 mimari (clarification gate eklendi):
  scope_check -> compress -> retriever -> (UC YOLLU GATE)
                                          ├── confidence  (dense_top < 0.60)
                                          ├── clarification (rerank_top < 0.50)
                                          └── generator -> claim_attribution -> confidence

clarification: kullaniciya hedefli takip sorusu sorar (Llama-3.3-70B). Loop max 2.
"""

from langgraph.graph import StateGraph, END

from app.graph.state import AgentState
from app.graph.nodes import (
    scope_check_node,
    compress_node,
    retriever_node,
    generator_node,
    claim_attribution_node,
    clarification_node,
    confidence_node,
)


def after_scope_check(state: dict) -> str:
    """Scope check sonrasi yonlendirme: out_of_scope ise direkt confidence."""
    if state.get("response_status") == "out_of_scope":
        return "confidence"
    return "compress"


# Confidence gate (eski) — dense COSINE skoru bunun altinda ise kaynak
# tamamen alakasiz, generator boşa kalır. Template fallback'e gönder.
EARLY_CONFIDENCE_THRESHOLD = 0.60

# Clarification gate (yeni v6) — dense yeterli ama BGE-reranker chunk'larin
# hicbirine güçlü bağ kuramadıysa, sorgu büyük olasilikla CIDDI BIÇIMDE
# AYIRICI TANIYA muhtaç ya da çok genel. Kullanıcıdan takip sorusu istenir.
# Sigmoid (rerank_score) 0.50 esigi — normal sorgu 0.95+, çok kötü 0.20-.
CLARIFY_RERANK_THRESHOLD = 0.50


def after_retriever(state: dict) -> str:
    """
    Retriever sonrasi yonlendirme — 3 yollu:

    1) dense_top < 0.60                      → "confidence" (template fallback)
    2) dense_top OK ama rerank_top < 0.50    → "clarification" (takip sorusu)
    3) ikisi de yeterli                       → "generator" (normal yol)

    Niye iki ayri threshold:
      - Dense yüksek + rerank düşük durumu MOST INFORMATIVE: kaynaklar var ama
        spesifik soruya cevap yok. Kullanıcıya soruyu daraltsın diyebiliriz.
      - Dense düşük durumu = kaynak havuzu konuyu hiç barındırmıyor →
        clarification atmak da boşa gider, direkt fallback.
    """
    top_sim = state.get("retrieval_similarity_score", 0.0)
    rerank = state.get("rerank_top_score", 0.0)

    if top_sim < EARLY_CONFIDENCE_THRESHOLD:
        return "confidence"
    if rerank < CLARIFY_RERANK_THRESHOLD:
        return "clarification"
    return "generator"


def build_graph() -> StateGraph:
    """LangGraph workflow'u olusturur ve derler."""
    graph = StateGraph(AgentState)

    graph.add_node("scope_check", scope_check_node)
    graph.add_node("compress", compress_node)
    graph.add_node("retriever", retriever_node)
    graph.add_node("generator", generator_node)
    graph.add_node("claim_attribution", claim_attribution_node)
    graph.add_node("clarification", clarification_node)
    graph.add_node("confidence", confidence_node)

    graph.set_entry_point("scope_check")

    graph.add_conditional_edges(
        "scope_check",
        after_scope_check,
        {"compress": "compress", "confidence": "confidence"},
    )

    graph.add_edge("compress", "retriever")

    # Retriever sonrasi 3 yollu gate
    graph.add_conditional_edges(
        "retriever",
        after_retriever,
        {
            "generator": "generator",
            "confidence": "confidence",
            "clarification": "clarification",
        },
    )

    # Normal yol: Generator -> Claim Attribution -> Confidence
    graph.add_edge("generator", "claim_attribution")
    graph.add_edge("claim_attribution", "confidence")

    # Clarification yolu: clarification -> confidence (skor verir, END)
    # Claim attribution gerekmez — clarification metninde claim yok, soru var.
    graph.add_edge("clarification", "confidence")

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
