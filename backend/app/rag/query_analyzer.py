"""
PaytarAI — Unified Query Analyzer

Tek LLM cagrisinda DORT isi birden:
  1) SCOPE detection (buyukbas hayvan kapsami mi?)
  2) Multi-HyDE (3 farkli hayali veteriner cevabi)
  3) Enriched keywords (TR+EN keyword listesi, rerank query icin)
  4) EN_QUERY: kullanici sorgusunun temiz Ingilizce cevirisi (cross-lingual
     rerank icin — EN chunk havuzunu kendi natif dilinde sorgulamak icin)

Niye birlestirildi:
  - Cerebras gpt-oss-120b'de scope_check ve enrich_query ayri cagri 429 queue overload
  - Groq tek call: ~700ms, tek prompt, hepsi
  - Out-of-scope ise downstream skip -> ek tasarruf

Model: OpenRouter llama-3.3-70b-instruct (paid tier)
Latency: ~700-1000ms (3 cagri yerine 1)

CROSS-LINGUAL BIAS MITIGATION (LAURA paper, ECIR 2020 keyword expansion findings):
  - BGE-reranker-v2-m3 cross-encoder TR sorgu + EN chunk pair'inde pair-level
    bias yapiyor (LAURA arxiv 2604.20199 paper'inda kanitlandi)
  - Keyword stuffing rerank query'sine zarar veriyor (ECIR 2020 + arxiv 2311.09175)
  - Cozum: TR pool kendi TR query ile, EN pool en_translated_query ile rerank.
    Native query-document language matching her iki dilde de BGE'nin en guclu
    setting'i. Keyword'ler artik sadece BM25/dense fazinda kullanilir, rerank
    query'sinden cikarildi.
"""

from langchain_openai import ChatOpenAI

from app.config import settings


ANALYZER_PROMPT = """Sen bir buyukbas (sigir, inek, buzagi) veteriner asistanisin.
Asagidaki kullanici sorusunu ALTI YONDEN analiz et ve TAM olarak belirtilen format'ta cevap ver.

KULLANICI SORUSU (multi-turn olabilir, parcalar `\\n\\n` ile ayrılmıştır):
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

ADIM 4 - EN_QUERY: Kullanicinin Turkce sorgusunu dogal, akici Ingilizceye CEVIR.
Veteriner literaturunde kullanilan dogru tibbi terimleri kullan (orn. "buzagi ishali"
-> "calf diarrhea", "sut hummasi" -> "milk fever / parturient paresis"). Kelime kelime
ceviri YAPMA, dogal soru cumlesi olarak ifade et. Eger sorgu zaten Ingilizceyse
oldugu gibi birak.

ADIM 5 - TR_RERANK: Sorguyu TIP KITABI / VETERINER DERS KITABI uslubunda
Turkce yeniden ifade et. Konusma dili degil, hekim dilinde TEK CUMLE. Multi-turn
ise tum bilgilerin OZUNU bir cumlede topla.

KURAL: TR_RERANK cumlesi BGE-reranker cross-encoder'a girecek; bu model
ders kitabi paragraflarini eslestirir. Cumle:
  - Hekim dilinde olsun ("ineklerde" degil "sigirlarda" tercih et)
  - Onemli klinik anahtar terimleri icermeli (ayirici tani, klinik bulgu,
    patogenez, tedavi yontemi gibi)
  - Soru cumlesi degil, ifade cumlesi olsun ("...nedir?" yerine "... ayirici tanisi")
  - Hayvani belirt (sigir, inek, buzagi, vb.)
  - 15-25 kelime arasi

ORNEKLER (good rewrites — bu kaliteyi yakala):
- In : "inegim saman yedi hastalandi"
  Out: "Sigirlarda saman tuketimi sonrasi gorulen gastrointestinal ve
        norolojik bozukluklarin ayirici tanisi"
- In : "inegim saman yedi\\n\\n5 yasinda, kan diski, ates 39.8"
  Out: "Eriskin sigirda saman tuketimi sonrasi gelisen ates, kanli ishal ve
        halsizlikle seyreden hastaliklarin ayirici tanisi"
- In : "buzagi ishali tedavisi"
  Out: "Yenidogan buzagilarda enterik ishalin etiyolojisi, klinik bulgular ve
        tedavi protokolu"
- In : "Holstein irki sut humması"
  Out: "Sut ineklerinde dogum sonrasi hipokalsemi (sut humması) patogenezi,
        klinik bulgular ve kalsiyum tedavisi"

ADIM 6 - EN_RERANK: Ayni ozeti TEK CUMLE Ingilizce TIP DILINDE yaz.
Veteriner ders kitabi (Rebhuns, Smith) uslubunda olsun.

ORNEKLER:
- "Differential diagnosis in adult cattle presenting with fever, bloody
   diarrhea and lethargy following hay ingestion"
- "Etiology, clinical findings and treatment of enteric diarrhea in newborn
   calves"
- "Pathogenesis, clinical signs and calcium therapy of postpartum
   hypocalcemia (milk fever) in dairy cows"

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
KEYWORDS: terim1, term2, terim3, terim4, ...
EN_QUERY: [Ingilizce dogal soru cumlesi]
TR_RERANK: [Turkce tibbi tek cumle]
EN_RERANK: [Ingilizce tibbi tek cumle]

Cevap:"""


_analyzer_llm: ChatOpenAI | None = None


def _get_analyzer_llm() -> ChatOpenAI:
    """OpenRouter llama-3.3-70b-instruct (paid tier)."""
    global _analyzer_llm
    if _analyzer_llm is None:
        _analyzer_llm = ChatOpenAI(
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            model="meta-llama/llama-3.3-70b-instruct",
            # TEMP=0: deterministik. Ayni sorgu her seferinde ayni HyDE +
            # ayni TR_RERANK + ayni EN_RERANK uretir. Onceki temp=0.2'de
            # rewrite kalitesinde her run'da +/- 0.1 sigmoid varyans goruluyordu.
            temperature=0,
            # 1200: 3 HyDE + KEYWORDS + EN_QUERY + TR_RERANK + EN_RERANK icin yeterli.
            max_tokens=1200,
            # PROVIDER PIN: Groq. Tum llama-3.3-70b cagrilari ayni provider'da
            # kalsin (latency/davranis tutarliligi). allow_fallbacks=False.
            extra_body={
                "provider": {"order": ["groq"], "allow_fallbacks": False}
            },
            default_headers={
                "HTTP-Referer": "https://github.com/paytar-ai",
                "X-Title": "PaytarAI",
            },
        )
    return _analyzer_llm


def analyze_query(query: str) -> dict:
    """
    Tek LLM cagrisinda scope + Multi-HyDE + keywords.

    Returns:
        {
            "is_in_scope": bool,
            "hyde_variants": list[str],      # 0-3 eleman
            "enriched_keywords": str,        # TR+EN keyword listesi (BM25/dense kanali icin)
            "en_translated_query": str,      # Tam Ingilizce cumle (EN pool rerank icin)
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
            "en_translated_query": "",
            "tr_rerank_query": "",
            "en_rerank_query": "",
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
            "en_translated_query": "",
            "tr_rerank_query": "",
            "en_rerank_query": "",
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
        "en_translated_query": "",
        "tr_rerank_query": "",  # ADIM 5 — TR rerank icin tibbi tek cumle
        "en_rerank_query": "",  # ADIM 6 — EN rerank icin tibbi tek cumle
        "raw_text": text,
        "error": None,
    }

    upper_text = text.upper()
    if "SCOPE: OUT" in upper_text or "SCOPE:OUT" in upper_text:
        result["is_in_scope"] = False
        return result

    # in-scope: parse hyde variants + keywords + en_query + tr_rerank + en_rerank
    # Hepsi "===" sonrasinda farkli satirlarda
    if "===" in text:
        before, after = text.split("===", 1)
        for line in after.strip().splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            upper = stripped.upper()
            if upper.startswith("KEYWORDS:"):
                value = stripped.split(":", 1)[1].strip()
                if value:
                    result["enriched_keywords"] = value
            elif upper.startswith("EN_QUERY:") or upper.startswith("EN-QUERY:") or upper.startswith("ENQUERY:"):
                value = stripped.split(":", 1)[1].strip()
                if value:
                    result["en_translated_query"] = value
            elif upper.startswith("TR_RERANK:") or upper.startswith("TR-RERANK:") or upper.startswith("TRRERANK:"):
                value = stripped.split(":", 1)[1].strip()
                if value:
                    result["tr_rerank_query"] = value
            elif upper.startswith("EN_RERANK:") or upper.startswith("EN-RERANK:") or upper.startswith("ENRERANK:"):
                value = stripped.split(":", 1)[1].strip()
                if value:
                    result["en_rerank_query"] = value
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
