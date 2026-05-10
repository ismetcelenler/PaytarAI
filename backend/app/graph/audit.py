"""
PaytarAI — Audit Logging Utility

AI-PROMPT.md Section 4.7: Tum kritik sistem aksiyonlari loglanir.
"""

from datetime import datetime, timezone


def audit_log(
    state: dict,
    action: str,
    reason: str | list | None = None,
    source_ids: list[str] | None = None,
) -> None:
    """
    Kritik aksiyon logları. Her entry sunlari icerir:
    - timestamp, request_id, user_role, model_used
    - action type, validation outcome, source identifiers

    ZORUNLU loglanmasi gereken aksiyonlar:
    - retrieval operations
    - dosage calculations
    - critic rejections
    - fallback triggers
    - tool executions
    - source references
    - final responses
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": state.get("request_id", "unknown"),
        "user_role": state.get("user_role", "unknown"),
        "model_used": state.get("active_model", "unknown"),
        "action": action,
        "reason": reason,
        "source_ids": source_ids or [],
        "evidence_confidence": state.get("evidence_confidence"),
        "critic_attempts": state.get("critic_attempts", 0),
    }

    if "audit_log" not in state:
        state["audit_log"] = []

    state["audit_log"].append(entry)
