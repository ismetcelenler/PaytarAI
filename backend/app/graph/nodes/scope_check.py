"""
PaytarAI — Scope Check Node (Unified Query Analyzer ile)

Eskiden ayri Cerebras LLM cagrisi yapardi. Simdi `query_analyzer.analyze_query()`
ile TEK Groq cagrisinda hem scope tespit eder hem de Multi-HyDE varyantlari +
enriched keywords uretir. State'e "query_analysis" field'i koyar; retriever_node
bunu okur, kendi LLM cagrilarini yapmaz.

Out-of-scope ise pipeline durdurulur.
"""

from app.rag.query_analyzer import analyze_query
from app.graph.audit import audit_log


OUT_OF_SCOPE_TEMPLATE = (
    "Bu konuda kesin bilgi veremem. "
    "Sistemimiz yalnızca büyükbaş hayvan (sığır, inek, buzağı, düve, dana) konularında "
    "bilgi sunabiliyor. Lütfen sorduğunuz konuyla ilgili uzmana ya da veteriner hekiminize danışın.\n\n"
    "⚠️ Bu bilgi karar desteğidir."
)


def scope_check_node(state: dict) -> dict:
    """
    Tek Groq cagrisi: scope + Multi-HyDE + keywords. Sonucu state'e koy.

    Out-of-scope ise:
      - retrieved_docs bos
      - final_response = OUT_OF_SCOPE_TEMPLATE
      - response_status = "out_of_scope"
    In-scope ise:
      - state["query_analysis"] = {is_in_scope, hyde_variants, enriched_keywords, ...}
      - downstream (retriever) bunu kullanir
    """
    messages = state.get("messages", [])
    if not messages:
        state["response_status"] = "error"
        return state

    # Son kullanici mesajini al
    last_user_msg = ""
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break
        elif hasattr(msg, "type") and msg.type == "human":
            last_user_msg = msg.content
            break

    if not last_user_msg:
        state["response_status"] = "error"
        return state

    analysis = analyze_query(last_user_msg)
    state["query_analysis"] = analysis

    if analysis["is_in_scope"]:
        audit_log(
            state,
            "scope_check_in_scope",
            reason=(
                f"hyde_variants={len(analysis['hyde_variants'])}, "
                f"keywords_len={len(analysis['enriched_keywords'])}, "
                f"err={analysis.get('error')}"
            ),
        )
        return state

    # Out-of-scope: sabit template don, downstream'i atla
    state["final_response"] = OUT_OF_SCOPE_TEMPLATE
    state["draft_response"] = OUT_OF_SCOPE_TEMPLATE
    state["response_status"] = "out_of_scope"
    state["retrieved_docs"] = []
    state["retrieval_similarity_score"] = 0.0
    state["source_agreement"] = False
    state["evidence_confidence"] = "insufficient"
    state["active_model"] = "query_analyzer (Groq llama-3.3-70b)"

    audit_log(
        state,
        "scope_check_out_of_scope",
        reason=f"analyzer: {analysis.get('raw_text', '')[:80]}",
    )

    return state
