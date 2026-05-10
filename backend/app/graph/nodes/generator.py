"""
PaytarAI — Generator Node

Groq Llama 3.3 70B ile rol bazli yanit uretir (ucretsiz).
Retrieved docs'u context olarak kullanir.
"""

from langchain_groq import ChatGroq
from app.config import settings
from app.graph.prompts import get_system_prompt
from app.graph.audit import audit_log


CONTEXT_TEMPLATE = """Asagida veteriner literaturunden alinan referans bilgiler bulunmaktadir.
Yanitini YALNIZCA bu kaynaklara dayanarak olustur. Kaynakta olmayan bilgiyi EKLEME.

ZORUNLU KURALLAR:
- Tum birimleri Turkiye standartlarina cevir: lb -> kg, gallon -> litre, oz -> mL, F -> C
- Kaynak referansi ekle (kitap adi, bolum)
- Turkce yaz

--- KAYNAKLAR ---
{sources}
--- KAYNAKLAR SONU ---

Kullanici sorusu: {question}"""


def generator_node(state: dict) -> dict:
    """
    Generator node — Groq Llama 3.3 70B ile yanit uretir (ucretsiz).

    Retrieved docs'u context olarak kullanir.
    Critic reddettiyse, red gerekceleriyle birlikte yeniden uretir.
    """
    messages = state.get("messages", [])
    retrieved_docs = state.get("retrieved_docs", [])
    user_role = state.get("user_role", "producer")

    # Son kullanici mesaji
    last_user_msg = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break

    if not last_user_msg:
        state["draft_response"] = "Soru anlasilamadi."
        state["response_status"] = "error"
        return state

    # Kaynak metinleri birlestir
    if retrieved_docs:
        sources_text = "\n\n".join(
            f"[Kaynak {i+1}] (Skor: {doc['score']:.2f}) "
            f"[{doc['metadata'].get('source_title', 'Bilinmeyen')}]\n{doc['text']}"
            for i, doc in enumerate(retrieved_docs[:5])
        )
    else:
        sources_text = "Hicbir kaynak bulunamadi."

    # Critic red gerekceleri varsa ekle
    rejection_context = ""
    rejection_reasons = state.get("critic_rejection_reasons", [])
    if rejection_reasons:
        rejection_context = (
            "\n\nONCEKI YANITIM REDDEDILDI. Reddi dikkate al:\n"
            + "\n".join(f"- {r}" for r in rejection_reasons)
            + "\nYukardaki sorunlari gidererek yeniden cevapla."
        )

    # Context prompt
    context_msg = CONTEXT_TEMPLATE.format(
        sources=sources_text,
        question=last_user_msg + rejection_context,
    )

    # System prompt
    system_prompt = get_system_prompt(user_role)

    try:
        llm = ChatGroq(
            api_key=settings.groq_api_key,
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=2000,
        )

        response = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context_msg},
        ])

        state["draft_response"] = response.content
        state["active_model"] = "llama-3.3-70b-versatile"
        state["response_status"] = "ok"

        audit_log(
            state,
            "generator_done",
            reason=f"role={user_role}, sources={len(retrieved_docs)}, attempt={state.get('critic_attempts', 0) + 1}",
        )

    except Exception as e:
        # Fallback — kaynak metni dogrudan sun
        state["draft_response"] = _build_fallback(retrieved_docs, user_role)
        state["response_status"] = "fallback"
        state["active_model"] = "fallback"
        audit_log(state, "generator_error", reason=str(e))

    return state


def _build_fallback(docs: list[dict], role: str) -> str:
    """LLM cagirisi basarisiz olursa kaynak metni dogrudan sunar."""
    if not docs:
        if role == "producer":
            return "Bu konuda bilgi bulunamadi. Veterinerinizi arayin."
        return "Bu konuda guvenilir literatur verisi dogrulanamadi. Lutfen baska bir kaynaga danisiniz."

    header = "Ilgili kaynak bilgileri:\n\n"
    for i, doc in enumerate(docs[:3]):
        header += f"{i+1}. {doc['text'][:500]}...\n\n"

    if role == "producer":
        header += "Bu bilgi karar destegidir. Uygulamadan once mutlaka bir veteriner hekime danisin."

    return header
