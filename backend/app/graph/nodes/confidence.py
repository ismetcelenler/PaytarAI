"""
PaytarAI — Confidence Scorer Node

Yanit guven skorunu belirler.
AI-PROMPT.md Section 4.6: high / medium / low / insufficient.
"""

from app.graph.audit import audit_log


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
