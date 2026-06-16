"""
PaytarAI — Step-Back Prompting

Spesifik kullanici sorgusunu DAHA GENIS bir kavramsal forma cevirir.
Boylece daha geniş bir aday havuzu retrieve edilir; spesifik soruya yanit
veren detay chunklar genis kapsamli paragraflarda yer alabilir.

Ornek:
  Soru:    "Mortellaro hastaligi kronik vakada prognoz?"
  Step-back: "Sigirlarda kronik topallik prognozu ve suru kontrol protokolleri"

  Soru:    "dogumdan 3 gun gecti sutum dusuk halsiz"
  Step-back: "Postpartum donemde inek metabolik problemleri (sut hummasi,
             ketozis, metritis) ve genel bakim"

Mantik:
  - Genis sorgu, embedding uzayinda daha cok chunk'a yakin durur
  - Spesifik sorudan kacirilan ilgili paragraflari yakalar
  - Production: %21.6 error rate dusumu (Step-Back paper)

Model: Groq llama-3.3-70b-versatile (hizli, ~300ms)
Reference: "Take a Step Back: Evoking Reasoning via Abstraction" (Google DeepMind 2024)
"""

from langchain_openai import ChatOpenAI
from app.config import settings


STEP_BACK_PROMPT = """Sen bir buyukbas (sigir, inek, buzagi) veteriner hekimisin.
Kullanicinin sordugu spesifik soruyu, daha GENIS ve KAVRAMSAL bir veteriner
sorusuna cevir. Amac: genis kategoride bilgi ararken hem orijinal soruyla
hem de ilgili komsu konularla eslesen icerige ulasmak.

Ornekler:
- "Mortellaro kronik prognoz" -> "Sigirlarda kronik topallik hastaliklari prognoz ve suru kontrolu"
- "dogumdan 3 gun gecti sutum dusuk halsiz" -> "Postpartum donemde inek metabolik bozukluklari ve klinik yaklasim"
- "kalsiyum boroglukonat aritmi" -> "Hipokalsemi tedavisinde IV kalsiyum uygulamasi ve riskleri"

Kurallar:
- TEK CUMLE yaz, soru cumlesi olmasin.
- Spesifik degerleri ya da dar terimi GENIS bir kavrama cevir.
- Buyukbas hayvan baglami koru.
- Hem Turkce hem yaygin Ingilizce terimleri ekle (orn. "ketozis (ketosis)").

Kullanici sorusu: {query}

Genis kavramsal form:"""


_sb_llm: ChatOpenAI | None = None


def _get_sb_llm() -> ChatOpenAI:
    """OpenRouter llama-3.3-70b-instruct (paid tier)."""
    global _sb_llm
    if _sb_llm is None:
        _sb_llm = ChatOpenAI(
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            model="meta-llama/llama-3.3-70b-instruct",
            # TEMP=0: deterministik step-back. Eski 0.1'de aynı sorguda her run
            # biraz farkli geri-adim cumlesi → farkli embedding → dense skor varyansi.
            temperature=0,
            max_tokens=120,
            default_headers={
                "HTTP-Referer": "https://github.com/paytar-ai",
                "X-Title": "PaytarAI",
            },
        )
    return _sb_llm


def generate_step_back(query: str) -> str | None:
    """
    Spesifik sorguyu genis kavramsal forma cevirir.

    Returns:
        Genis sorgu metni (tek cumle) veya None.
    """
    if not query or len(query.strip()) < 3:
        return None

    try:
        import re as _re
        import time as _time

        prompt = STEP_BACK_PROMPT.format(query=query.strip())
        llm = _get_sb_llm()

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
                print(f"[Step-Back] Rate limit, {wait_s:.1f}s bekle ({attempt+1}/{max_retries})")
                _time.sleep(wait_s)

        text = str(response.content).strip()
        # Bazen "Genis kavramsal form:" gibi prefix sizar — temizle
        text = text.replace("Genis kavramsal form:", "").strip().strip(":").strip()
        if len(text) < 10:
            return None
        return text

    except Exception as e:
        print(f"[Step-Back] hata: {e}")
        return None
