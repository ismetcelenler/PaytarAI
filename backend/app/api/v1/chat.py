"""
PaytarAI — Chat Endpoint (SSE Streaming)

LangGraph workflow'unu tetikler ve SSE stream olarak yanıt döner.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Chat"])


class ChatRequest(BaseModel):
    """Chat isteği modeli."""
    message: str
    user_role: str  # "veterinarian" | "producer"
    thread_id: str | None = None
    animal_weight_kg: float | None = None
    input_source: str = "text"  # "text" | "voice"


class ChatResponse(BaseModel):
    """Chat yanıt modeli (non-streaming fallback)."""
    response: str
    thread_id: str
    evidence_confidence: str
    sources: list[dict] = []
    audit_entry_count: int = 0


@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Chat endpoint — LangGraph workflow'unu çalıştırır.

    TODO (Faz 3): LangGraph entegrasyonu
    - SSE streaming implementasyonu
    - Rol bazlı prompt injection
    - Tool calling (dosage, retrieval)
    """
    # Placeholder response — Faz 3'te LangGraph ile değiştirilecek
    if request.user_role == "veterinarian":
        placeholder = (
            "⚕️ [Veteriner Modu] Sistem başlatılıyor. "
            "LangGraph workflow entegrasyonu Faz 3'te tamamlanacak."
        )
    else:
        placeholder = (
            "🐄 [Üretici Modu] Sistem başlatılıyor. "
            "LangGraph workflow entegrasyonu Faz 3'te tamamlanacak.\n\n"
            "⚠️ Bu bilgi karar desteğidir. Uygulamadan önce mutlaka bir veteriner hekime danışın."
        )

    return ChatResponse(
        response=placeholder,
        thread_id=request.thread_id or "temp-thread-001",
        evidence_confidence="insufficient",
        sources=[],
        audit_entry_count=0,
    )
