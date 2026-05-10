"""
PaytarAI — Compress Node

State cok buyukse (token limiti) Groq/Llama 3.3 70B ile ozetler.
AI-PROMPT.md Section 4.2.
"""

from langchain_groq import ChatGroq
from app.config import settings
from app.graph.audit import audit_log


COMPRESSION_PROMPT = """Asagidaki konusma gecmisini, en onemli klinik bilgileri
(hayvan bilgisi, semptomlar, yapilan tedaviler, test sonuclari) koruyarak
kisa bir ozet haline getir. Dozaj bilgilerini ASLA dusurme.

Konusma:
{conversation}

Ozet:"""


def compress_node(state: dict) -> dict:
    """
    State compression node.
    Konusma gecmisi cok uzunsa Llama 3.3 ile ozetler.
    """
    messages = state.get("messages", [])

    # Token tahmini: ~4 karakter = 1 token
    total_chars = sum(len(m.get("content", "")) for m in messages)
    estimated_tokens = total_chars / 4

    # 6000 token'dan kucukse sikistirmaya gerek yok
    if estimated_tokens < 6000 or len(messages) < 8:
        audit_log(state, "compress_skip", reason="Token limiti altinda")
        return state

    # Son 2 mesaji koru, gerisini ozetle
    recent = messages[-2:]
    to_compress = messages[:-2]

    conversation_text = "\n".join(
        f"{m.get('role', 'user')}: {m.get('content', '')}"
        for m in to_compress
    )

    try:
        llm = ChatGroq(
            api_key=settings.groq_api_key,
            model="llama-3.3-70b-versatile",
            temperature=0,
            max_tokens=500,
        )

        prompt = COMPRESSION_PROMPT.format(conversation=conversation_text)
        response = llm.invoke(prompt)
        summary = response.content

        state["compression_summary"] = summary
        state["active_model"] = "llama-3.3-70b-versatile"

        # Mesajlari sikistirilmis haliyle degistir
        state["messages"] = [
            {"role": "system", "content": f"[Onceki konusma ozeti]: {summary}"},
            *recent,
        ]

        audit_log(state, "compress_done", reason=f"Compressed {len(to_compress)} messages")

    except Exception as e:
        # Sikistirma basarisiz olursa original state ile devam et
        audit_log(state, "compress_error", reason=str(e))

    return state
