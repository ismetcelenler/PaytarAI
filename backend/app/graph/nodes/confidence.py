"""
PaytarAI — Confidence Scorer Node

Yanit guven skorunu belirler.
AI-PROMPT.md Section 4.6: high / medium / low / insufficient.

YENI (Phase 0): Confidence threshold gate
- Eger top_sim < INSUFFICIENT_THRESHOLD ise generator yanitini KULLANMAYIZ,
  sabit template ile degistiririz. Bu kaynaki yetersiz konularda halusinasyonu
  onler (orn. Holstein irk bilgisi gibi kaynaklarda zayif olan konular).
"""

from app.graph.audit import audit_log


INSUFFICIENT_THRESHOLD = 0.60  # BGE-M3 sonrasi kalibre (eski deger 0.45 idi).
# In-scope sorularda min top_sim ~0.67, out-of-scope (Holstein gibi) ~0.54.
# 0.60 esigi ikisini ayirir, halusinasyonu engeller.

LOW_CONFIDENCE_TEMPLATE_PRODUCER = (
    "Bu konuda kaynaklarımda yeterli bilgi bulamadım. "
    "Lütfen veterinerinize danışın.\n\n"
    "⚠️ Sistem yalnızca kaynaklarımda olan büyükbaş hayvan konularında bilgi verebilir."
)

LOW_CONFIDENCE_TEMPLATE_VET = (
    "Bu konuda elimdeki kaynaklarda güvenilir bir bilgi bulamadım, "
    "farklı bir kaynak incelemenizi öneririm."
)


def confidence_node(state: dict) -> dict:
    """
    Confidence scorer — 4 faktore gore guven skoru hesaplar:
    1. Retrieval similarity skoru
    2. Kaynak uyumu (birden fazla kaynak ayni bilgiyi dogruluyor mu)
    3. Critic red sayisi
    4. Response status
    """
    similarity = state.get("retrieval_similarity_score", 0.0)
    agreement = state.get("source_agreement", False)
    attempts = state.get("critic_attempts", 0)
    status = state.get("response_status", "ok")
    docs = state.get("retrieved_docs", [])
    user_role = state.get("user_role", "producer")

    # === PHASE 0 GATE: scope_check zaten template koyduysa devam etme ===
    if status == "out_of_scope":
        state["evidence_confidence"] = "insufficient"
        # final_response zaten set edilmis
        audit_log(state, "confidence_skip_oos", reason="scope_check out_of_scope")
        return state

    # === CLARIFICATION GATE: clarification_node zaten final_response koydu, ezme ===
    # response_status = "clarification_needed" veya "clarification_exhausted"
    if status in ("clarification_needed", "clarification_exhausted"):
        # evidence_confidence clarification_node icinde set edildi (low/insufficient)
        audit_log(state, "confidence_skip_clarification",
                  reason=f"status={status}, attempts={state.get('clarification_attempts', 0)}")
        return state

    # === PHASE 0 GATE: dusuk similarity ise generator yanitini ezip template ver ===
    if similarity < INSUFFICIENT_THRESHOLD and similarity > 0:
        template = LOW_CONFIDENCE_TEMPLATE_PRODUCER if user_role == "producer" else LOW_CONFIDENCE_TEMPLATE_VET
        state["final_response"] = template
        state["draft_response"] = template
        state["evidence_confidence"] = "insufficient"
        state["response_status"] = "insufficient_evidence"
        audit_log(
            state,
            "confidence_low_sim_gate",
            reason=f"top_sim={similarity:.3f} < threshold={INSUFFICIENT_THRESHOLD}, template fallback",
        )
        return state

    # Skor hesapla
    score = 0

    # 1. Retrieval similarity (0-40 puan)
    if similarity >= 0.65:
        score += 40
    elif similarity >= 0.50:
        score += 25
    elif similarity >= 0.40:
        score += 10

    # 2. Kaynak sayisi ve uyumu (0-25 puan)
    if len(docs) >= 3 and agreement:
        score += 25
    elif len(docs) >= 2:
        score += 15
    elif len(docs) >= 1:
        score += 5

    # 3. Critic basarisi (0-20 puan)
    if attempts == 0:
        score += 20  # Ilk denemede gecti
    elif attempts == 1:
        score += 10  # 1 red sonrasi gecti

    # 4. Response status (0-15 puan)
    if status == "accepted":
        score += 15
    elif status == "accepted_after_max_retries":
        score += 5
    elif status == "fallback":
        score += 0

    # Confidence seviyesi belirle
    if score >= 75:
        confidence = "high"
    elif score >= 50:
        confidence = "medium"
    elif score >= 25:
        confidence = "low"
    else:
        confidence = "insufficient"

    state["evidence_confidence"] = confidence

    audit_log(
        state,
        "confidence_scored",
        reason=f"score={score}, confidence={confidence}, sim={similarity:.3f}, docs={len(docs)}, attempts={attempts}",
    )

    return state
