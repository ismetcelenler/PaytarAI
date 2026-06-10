"""
PaytarAI — AgentState Definition

LangGraph workflow state şeması. AI-PROMPT.md Section 4.1'e uygun.
"""

from typing import TypedDict, Literal


class AgentState(TypedDict):
    """LangGraph agent state — tüm node'lar arasında paylaşılır."""

    # Konuşma mesajları
    messages: list[dict]

    # Retrieval sonuçları
    retrieved_docs: list[dict]

    # Tool çıktıları (dosage, drug_lookup vb.)
    tool_outputs: dict

    # Thread-scoped memory
    thread_memory: dict

    # Critic döngü sayacı (max 2)
    critic_attempts: int

    # State sıkıştırma özeti (Llama 3.3 ile)
    compression_summary: str

    # Yanıt durumu: "ok" | "fallback" | "error" | "rejected"
    response_status: str

    # Kullanıcı rolü — login'den inject edilir
    user_role: Literal["veterinarian", "producer"]

    # Girdi kaynağı — UI'dan inject edilir
    input_source: Literal["text", "voice"]

    # Kanıt güven skoru
    evidence_confidence: Literal["high", "medium", "low", "insufficient"]

    # Audit log — her kritik aksiyonun kaydı
    audit_log: list[dict]

    # --- Ek alanlar (workflow içinde kullanılır) ---

    # Taslak yanıt (Critic'e gönderilir)
    draft_response: str

    # Critic red gerekçeleri
    critic_rejection_reasons: list[str]

    # Final yanıt (kullanıcıya gönderilir)
    final_response: str

    # Request ID (izlenebilirlik)
    request_id: str

    # Aktif model adı
    active_model: str

    # Retrieval similarity score (DENSE cosine — confidence gate bunu kullanir)
    retrieval_similarity_score: float

    # Reranker top score (cross-encoder sigmoid output, audit/log icin)
    rerank_top_score: float

    # Kaynak uyumu (birden fazla kaynak aynı bilgiyi doğruluyor mu)
    source_agreement: bool

    # Dozaj triplet doğrulandı mı
    dosage_triplet_validated: bool

    # Kaynak güven seviyesi (1-6)
    source_trust_level: int
