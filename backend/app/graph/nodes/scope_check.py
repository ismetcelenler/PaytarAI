"""
PaytarAI — Scope Check Node (Unified Query Analyzer ile)

Eskiden ayri Cerebras LLM cagrisi yapardi. Simdi `query_analyzer.analyze_query()`
ile TEK Groq cagrisinda hem scope tespit eder hem de Multi-HyDE varyantlari +
enriched keywords uretir. State'e "query_analysis" field'i koyar; retriever_node
bunu okur, kendi LLM cagrilarini yapmaz.

Out-of-scope ise pipeline durdurulur.
"""

import time

from app.rag.query_analyzer import analyze_query
from app.graph.audit import audit_log
from app.graph.debug_trace import trace_node, trim_text


OUT_OF_SCOPE_TEMPLATE = (
    "Bu konuda kesin bilgi veremem. "
    "Sistemimiz yalnızca büyükbaş hayvan (sığır, inek, buzağı, düve, dana) konularında "
    "bilgi sunabiliyor. Lütfen sorduğunuz konuyla ilgili uzmana ya da veteriner hekiminize danışın.\n\n"
    "⚠️ Bu bilgi karar desteğidir."
)


def scope_check_node(state: dict) -> dict:
    """
    Tek Groq cagrisi: scope + Multi-HyDE + keywords. Sonucu state'e koy.
    """
    t0 = time.perf_counter()
    messages = state.get("messages", [])
    if not messages:
        state["response_status"] = "error"
        return state

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
    latency_ms = (time.perf_counter() - t0) * 1000

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
        trace_node(
            state, "scope_check",
            input={"user_message": last_user_msg},
            output={
                "decision": "in_scope",
                "raw_analyzer": trim_text(analysis.get("raw_text", ""), 1500),
                "hyde_variants": analysis.get("hyde_variants", []),
                "enriched_keywords": analysis.get("enriched_keywords", ""),
                "error": analysis.get("error"),
            },
            latency_ms=latency_ms,
        )
        return state

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
    trace_node(
        state, "scope_check",
        input={"user_message": last_user_msg},
        output={
            "decision": "out_of_scope",
            "raw_analyzer": trim_text(analysis.get("raw_text", ""), 1500),
            "fallback_response": OUT_OF_SCOPE_TEMPLATE,
        },
        latency_ms=latency_ms,
    )

    return state
