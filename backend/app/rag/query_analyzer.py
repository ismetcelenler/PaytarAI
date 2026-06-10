"""
PaytarAI — Unified Query Analyzer

Tek LLM cagrisinda UC isi birden:
  1) SCOPE detection (buyukbas hayvan kapsami mi?)
  2) Multi-HyDE (3 farkli hayali veteriner cevabi)
  3) Enriched keywords (TR+EN keyword listesi, rerank query icin)

Niye birlestirildi:
  - Cerebras gpt-oss-120b'de scope_check ve enrich_query ayri cagri 429 queue overload
  - Groq tek call: ~700ms, tek prompt, hepsi
  - Out-of-scope ise downstream skip -> ek tasarruf

Model: Groq llama-3.3-70b-versatile
Latency: ~700-1000ms (3 cagri yerine 1)
"""

from langchain_openai import ChatOpenAI

from app.config import settings


ANALYZER_PROMPT = """Sen bir buyukbas (sigir, inek, buzagi) veteriner asistanisin.
Asagidaki kullanici sorusunu UC YONDEN analiz et ve TAM olarak belirtilen format'ta cevap ver.

KULLANICI SORUSU:
{query}

ADIM 1 - SCOPE: Bu soru buyukbas hayvan (sigir/inek/buzagi/duve/dana/boga) sagligi,
beslenmesi, uremesi veya cifclik yonetimi ile ilgili mi?
- EVET ornekleri: "inegim sutu dustu", "buzagi ishal", "kizginlik", "holstein"
- HAYIR ornekleri: "kedi", "kopek", "kus", "at", "tavuk", "bitki", "tarla"
- Eger kapsam disi ise SADECE "SCOPE: OUT" yaz, gerisini ATLA.
- Eger kapsam icindeyse "SCOPE: IN" yaz ve adim 2'ye gec.

ADIM 2 - 3 HAYALI ACIKLAMA: Eger SCOPE: IN ise, soruya yonelik 3 FARKLI olasi
teshis/durum hakkinda 2-3 cumlelik kisa veteriner aciklamasi yaz. Hastalik adlarini
hem Turkce hem yaygin Ingilizce karsiliklariyla yaz (orn. "sut hummasi / milk fever").
Spesifik dozaj YAZMA. Aciklamalar "---" ile ayrilsin.

ADIM 3 - KEYWORDS: Hayali aciklamalardan TR+EN veteriner terimlerini virgulle
ayrilmis bir liste olarak yaz. Cumle kurma, sadece terimler.

KESIN FORMAT (out-of-scope durumu):
SCOPE: OUT

KESIN FORMAT (in-scope durumu):
SCOPE: IN
---
[Hayali aciklama 1]
---
[Hayali aciklama 2]
---
[Hayali aciklama 3]
===
KEYWORDS: terim1, term2, terim3, term4, ...

Cevap:"""


_analyzer_llm: ChatOpenAI | None = None


def _get_analyzer_llm() -> ChatOpenAI:
    global _analyzer_llm
    if _analyzer_llm is None:
        _analyzer_llm = ChatOpenAI(
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            max_tokens=900,  # 3 HyDE + keywords icin marj
        )
    return _analyzer_llm


def analyze_query(query: str) -> dict:
    """
    Tek LLM cagrisinda scope + Multi-HyDE + keywords.

    Returns:
        {
            "is_in_scope": bool,
            "hyde_variants": list[str],      # 0-3 eleman
            "enriched_keywords": str,        # TR+EN keyword listesi (rerank query icin)
            "raw_text": str,                 # debug icin
            "error": str | None,
        }

    Hata durumunda: is_in_scope=True (default), variants=[], keywords="" doner.
    """
    if not query or len(query.strip()) < 3:
        return {
            "is_in_scope": True,
            "hyde_variants": [],
            "enriched_keywords": "",
            "raw_text": "",
            "error": "empty query",
        }

    try:
        import re as _re
        import time as _time

        prompt = ANALYZER_PROMPT.format(query=query.strip())
        llm = _get_analyzer_llm()

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
                print(f"[QueryAnalyzer] Rate limit, {wait_s:.1f}s bekle ({attempt+1}/{max_retries})")
                _time.sleep(wait_s)

        text = str(response.content).strip()
        return _parse_analyzer_output(text)

    except Exception as e:
        print(f"[QueryAnalyzer] hata: {e} — in-scope default")
        return {
            "is_in_scope": True,
            "hyde_variants": [],
            "enriched_keywords": "",
            "raw_text": "",
            "error": str(e),
        }


def _parse_analyzer_output(text: str) -> dict:
    """
    Format:
        SCOPE: IN|OUT
        ---
        [hyde 1]
        ---
        [hyde 2]
        ---
        [hyde 3]
        ===
        KEYWORDS: kw1, kw2, ...
    """
    result = {
        "is_in_scope": True,  # default
        "hyde_variants": [],
        "enriched_keywords": "",
        "raw_text": text,
        "error": None,
    }

    upper_text = text.upper()
    if "SCOPE: OUT" in upper_text or "SCOPE:OUT" in upper_text:
        result["is_in_scope"] = False
        return result

    # in-scope: parse hyde variants + keywords
    # Keywords genelde "===" sonrasinda
    if "===" in text:
        before, after = text.split("===", 1)
        # Keywords parse
        kw_lines = [l.strip() for l in after.strip().splitlines() if l.strip()]
        for line in kw_lines:
            # "KEYWORDS:" prefix kaldir
            if ":" in line:
                line = line.split(":", 1)[1]
            kw = line.strip()
            if kw:
                result["enriched_keywords"] = kw
                break
    else:
        before = text

    # SCOPE: IN satirini cikar, --- ile bol
    lines = before.splitlines()
    body_lines = []
    for line in lines:
        if line.strip().upper().startswith("SCOPE"):
            continue
        body_lines.append(line)
    body = "\n".join(body_lines).strip()

    variants = [v.strip() for v in body.split("---") if len(v.strip()) >= 30]
    result["hyde_variants"] = variants[:3]
    return result
