"""
PaytarAI — Multi-HyDE (Hypothetical Document Embeddings)

Kullanici sorgusundan N farkli hayali veteriner cevabi uretir (her biri farkli
olasi teshise odakli). Her biri embed edilip dense search'te ayri kanal olarak
kullanilir; RRF gibi mantikla birlestirilir.

Mantik:
  - Tek HyDE: tek anchor noktasi -> retrieval narrow
  - Multi-HyDE (3 varyant): 3 farklı yondan anchor -> retrieval recall artar
  - Production: Multi-HyDE +%34 -> +%46 accuracy (Multi-HyDE paper 2025)

Model: Groq llama-3.3-70b-versatile (reasoning yok, hizli)
Reference: Multi-HyDE (arxiv 2509.16369), DMFlow.chat RAG transformation guide 2026
"""

from langchain_openai import ChatOpenAI
from app.config import settings


# Tek LLM cagrisinda 3 varyant uret — token cost = tek HyDE seviyesinde
MULTI_HYDE_PROMPT = """Sen bir buyukbas (sigir, inek, buzagi) veteriner hekimisin.
Asagidaki kullanici sorusu icin UC FARKLI olasi teshis/durumu temel alan
kisa aciklamalar yaz. Her aciklama 2-3 cumle olsun, gercek bir veteriner
referans kitabindan aliniyormus gibi yaz.

Kullanici sorusu: {query}

KURALLAR:
- 3 aciklama olsun, "---" ile ayrilsin.
- Her aciklama FARKLI bir olasi teshise/duruma odaklansin.
- Hastalik adlarini hem Turkce hem Ingilizce karsiliklariyla yaz (orn. "sut hummasi / milk fever").
- Spesifik dozaj YAZMA.
- Cevabin gercek olmasi sart degil — amac vektor uzayinda dogru chunklara semantik anchor.

Format:
[Olasi teshis 1 hakkinda kisa aciklama]
---
[Olasi teshis 2 hakkinda kisa aciklama]
---
[Olasi teshis 3 hakkinda kisa aciklama]

Cevap:"""


_hyde_llm: ChatOpenAI | None = None


def _get_hyde_llm() -> ChatOpenAI:
    global _hyde_llm
    if _hyde_llm is None:
        _hyde_llm = ChatOpenAI(
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
            model="llama-3.3-70b-versatile",
            temperature=0.3,  # yaraticilik: 3 farkli teshis icin biraz cesitlilik
            max_tokens=600,   # 3 varyant x ~150 token
        )
    return _hyde_llm


def generate_multi_hyde(query: str, n: int = 3) -> list[str]:
    """
    Kullanici sorgusu icin N farkli hayali veteriner cevabi uretir.

    Returns:
        Liste (en fazla n eleman) — her biri kisa hipotetik cevap.
        Bos liste donerse retrieval'a fayda etmez (HyDE'siz arama).
    """
    if not query or len(query.strip()) < 3:
        return []

    try:
        import re as _re
        import time as _time

        prompt = MULTI_HYDE_PROMPT.format(query=query.strip())
        llm = _get_hyde_llm()

        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                response = llm.invoke(prompt)
                break
            except Exception as rate_err:
                msg = str(rate_err)
                if "rate_limit" not in msg.lower() and "429" not in msg:
                    raise
                if attempt >= max_retries:
                    raise
                wait_match = _re.search(r"try again in ([\d.]+)s", msg)
                wait_s = float(wait_match.group(1)) + 1.0 if wait_match else 5.0
                print(f"[Multi-HyDE] Rate limit, {wait_s:.1f}s bekle ({attempt+1}/{max_retries})")
                _time.sleep(wait_s)

        text = str(response.content).strip()
        if len(text) < 30:
            return []

        # "---" ile ayir
        variants = [v.strip() for v in text.split("---") if len(v.strip()) >= 30]
        return variants[:n]

    except Exception as e:
        print(f"[Multi-HyDE] hata: {e}")
        return []


# Backward compat — eski tek HyDE cagrilari
def generate_hyde(query: str) -> str | None:
    """Backward compat: Multi-HyDE'nin ilk varyantini doner."""
    variants = generate_multi_hyde(query, n=1)
    return variants[0] if variants else None
