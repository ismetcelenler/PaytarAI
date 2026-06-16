"""
PaytarAI — Per-Claim Citation Attribution (Faz C)

LettuceDetect (v3) tamamen kaldirildi. Yerine geldigi mantik:
  1) Yaniti cumlelere bol.
  2) Tek LLM cagrisinda her cumle icin:
       - "claim" mi (spesifik tibbi iddia) yoksa "filler" mi
         (disclaimer, sevk, gozlem, gecis, baslik) sinifla.
       - "claim" ise: Hangi Kaynak (1..N) destekliyor? Hicbiri yoksa drop.
       - "filler" ise: kaynak gerektirmez, korunur.
  3) Korunan cumleleri tekrar birlestir. Claim cumlelerinin sonuna inline
     `[Kaynak N]` etiketi koy — frontend tiklanabilir hale getirir.

Niye boyle:
  LettuceDetect mini-eval'de 13/13 drop yanlis verdi (research/eval_report_2026-06-13.md).
  Token-level classifier liste maddesi, disclaimer, atif satirlarini halusinasyon
  saniyordu. Bu node onun yerine "her cumle bir karara baglansin" prensibiyle
  her cumleyi tek tek elden gecirir. Tanilanabilir bir kuyruk: drop sebebi artik
  "bu cumle bir iddiadir ve hicbir chunk'a baglanmiyor" — net.

Model: meta-llama/llama-3.3-70b-instruct (OpenRouter). query_analyzer ile ayni
deploy, ucuz, TR/EN cross-lingual yetenekli.
"""

from __future__ import annotations

import json
import re
import time

from langchain_openai import ChatOpenAI

from app.config import settings
from app.graph.audit import audit_log
from app.graph.debug_trace import trace_node, trim_text


# ─────────────────────────────────────────────────────────────────
# GENERATOR ARTIK TEMIZLIGI
# ─────────────────────────────────────────────────────────────────
# Generator bazen prompt'a ragmen "[Kaynak: ...]", "【Referans N】",
# "Kaynak: Kitap Adi, ilgili bolum" tipi atif satirlari uretiyor. Bizim
# sistemimiz tek atif formati [Kaynak N] (ASCII bracket + sayi) — bunun
# disindakileri attribution'dan ONCE temizleriz, yoksa cumle bolme sirasinda
# karisikliga yol acar.

_NOISE_CITATION_RE = re.compile(
    # [Kaynak: Kitap Adi]  /  【Kaynak: ...】  (colon variant)
    r"[\[【〖]\s*(?:Kaynak|Referans|Ref|Bkz)\s*[:：][^\]】〗\n]*[\]】〗]"
    r"|"
    # [Kaynak 1] / 【Kaynak 1】 / 【Referans 4】  (number variant — yargı oncesi temizlenir,
    # bizim kendi [Kaynak N] etiketimizi sonradan _reassemble ekleyecek)
    r"[\[【〖]\s*(?:Kaynak|Referans|Ref|Bkz)\s+\d+\s*[\]】〗]"
    r"|"
    # Baslayan satir: "Kaynak: ..." / "Referans: ..."
    r"^\s*(?:Kaynak|Referans|Ref|Bkz)\s*[:：][^\n]*$",
    flags=re.MULTILINE,
)


def _strip_generator_citations(text: str) -> str:
    """Generator'in yerlestirdigi yanlis formatli atiflari sil. Sistem
    [Kaynak N] ekleyecek; bu fonksiyon onun yolundaki gurultu temizler."""
    out = _NOISE_CITATION_RE.sub("", text)
    # Birden fazla bosluk / cift noktalama temizligi
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\s+\.\s*", ". ", out)
    return out.strip()


# ─────────────────────────────────────────────────────────────────
# CUMLE BOLME
# ─────────────────────────────────────────────────────────────────
#
# Lookahead BUYUK harf/asterisk/tire/rakam — yoksa bolme. Bu sayede
# "E. coli", "Cl. perfringens", "S. typhimurium" gibi tibbi kisaltmalarda
# nokta sonrasi kucuk harf gelirse cumle SINIRI sayilmaz, organizma adi
# bolunmez. (Hata: "Bakteriyel ... **E. | coli**, **Cl. | perfringens**..."
# her noktadan kesiyordu.)

_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-ZĞÜŞİÖÇ\*\-0-9])")


def _split_sentences(text: str) -> list[str]:
    """Yaniti cumlelere bol. Bullet/numbered list satirlari tek cumle."""
    out: list[str] = []
    for line in re.split(r"(\n+)", text):
        if not line.strip():
            continue
        if re.match(r"^\s*(\*\*|[-*]|\d+\.)", line):
            out.append(line.strip())
            continue
        for piece in _SENT_SPLIT_RE.split(line):
            piece = piece.strip()
            if piece:
                out.append(piece)
    return out


# ─────────────────────────────────────────────────────────────────
# LLM SINGLETON
# ─────────────────────────────────────────────────────────────────

_judge_llm: ChatOpenAI | None = None
_verifier_llm: ChatOpenAI | None = None

# ─────────────────────────────────────────────────────────────────
# VERIFIER FEATURE FLAG
# ─────────────────────────────────────────────────────────────────
# 2026-06-15: Verifier devre disi birakildi. Sebep:
#   - Generator + judge + hardcode substring verify zaten yuksek rerank skorlu
#     sorgularda iyi yanit + dogru chunk_id uretiyor.
#   - LLM verifier (Opus, Sonnet, Gemini, Scout, gpt-oss) farklı modellerde
#     denendi; quote secimi tablolu kaynaklarda yetersiz kalip yanlis cumleyi
#     highlight'a koyuyordu. Bu UX'i bozdugu icin devre disi.
#   - True yapilirsa _verify_evidence_with_llm yine cagrilir.
VERIFIER_ENABLED = False


def _get_judge_llm() -> ChatOpenAI:
    """Llama-3.3-70B (OpenRouter, default provider) — 1. asama: claim/filler
    siniflandirma + chunk_id ilk tahmin + evidence taslagi."""
    global _judge_llm
    if _judge_llm is None:
        _judge_llm = ChatOpenAI(
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            model="meta-llama/llama-3.3-70b-instruct",
            temperature=0,
            max_tokens=2000,
            # JSON-only output zorla: OpenRouter response_format destegi vardir,
            # cikti markdown sarmali / aciklama gelmez.
            model_kwargs={"response_format": {"type": "json_object"}},
            # PROVIDER PIN: Groq (tum llama-3.3-70b cagrilari ayni provider'da).
            extra_body={
                "provider": {"order": ["groq"], "allow_fallbacks": False}
            },
            default_headers={
                "HTTP-Referer": "https://github.com/paytar-ai",
                "X-Title": "PaytarAI",
            },
        )
    return _judge_llm


def _get_verifier_llm() -> ChatOpenAI:
    """2. asama LLM verifier — anlamsal entailment + verbatim pasaj cikarimi.

    Model: openai/gpt-oss-120b @ OpenRouter, reasoning_effort=high.
      - Llama 4 Scout ve Gemini 2.5 Flash claim ↔ chunk_id'yi dogru buluyor ama
        chunk icinde "iddiayi destekleyen spesifik cumleyi" yanlis seciyordu
        (uzun chunk + birden cok alt-konu sebebiyle). Bu reasoning gorevi —
        thinking-mode model gerekli.
      - gpt-oss-120b zaten generator'de medium reasoning ile kullaniliyor.
        Verifier'da quote secimi daha kritik (frontend highlight icin), high
        effort verdik. Yaklasik donus 2-4s.
    """
    global _verifier_llm
    if _verifier_llm is None:
        _verifier_llm = ChatOpenAI(
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            # Opus 4.8: smoke test'te en yuksek quote isabeti (4/5 mukemmel,
            # bilincli drop). Sonnet 4.6 ayni sorguda 2/4 mukemmel + %56 drop
            # ratio ile geri kaldi (tablolu kaynaklarda yetersiz). Highlighting
            # kalitesi UX icin kritik oldugundan Opus tercih edildi.
            model="anthropic/claude-opus-4-8",
            temperature=0,
            max_tokens=3000,
            model_kwargs={"response_format": {"type": "json_object"}},
            default_headers={
                "HTTP-Referer": "https://github.com/paytar-ai",
                "X-Title": "PaytarAI",
            },
        )
    return _verifier_llm


# ─────────────────────────────────────────────────────────────────
# PROMPT
# ─────────────────────────────────────────────────────────────────

JUDGE_PROMPT = """Sen bir kaynak-dogrulama uzmanisin. Asagidaki YANITI cumle cumle degerlendir.

KAYNAKLAR:
{sources}

YANIT (numarali cumleler):
{sentences}

HER CUMLE ICIN su karari ver:

1) TYPE:
   - "filler"  : Net spesifik iddiasi OLMAYAN cumleler. Sunlar filler:
                 ✓ Konu/paragraf girisi ("X bircok faktorden olabilir",
                   "Y'nin nedenleri arasinda sunlar yer alir",
                   "Bu durumda dikkat edilmesi gereken kanitlar vardir")
                 ✓ Gecis/baglac cumlesi, ozetleme, sonuc ifadesi
                 ✓ Surec tavsiyesi ("bilgileri toplamak onemlidir",
                   "ilk adim olarak X sorgulanmalidir") — yontem onerisi,
                   spesifik tibbi veri degil
                 ✓ Disclaimer ("⚠️ Bu bilgi karar destegidir")
                 ✓ Sevk talimati ("veterinerinize basvurun")
                 ✓ Gozlem talimati ("ates olc", "dışkıyı izle")
                 ✓ Tehlike isareti esigi ("40°C'yi gecerse")
                 ✓ Acil sevk uyarisi ("DERHAL VETERINERE BASVURUN")
                 -> kaynak GEREKMEZ, KEEP.
   - "claim"   : Spesifik tibbi iddia. Sunlar claim:
                 ✓ Hastalik adi + neden ("mastitis, meme iltihabi")
                 ✓ Sayisal deger + neye ait ("%5-25 azalma", "8-15 mg/dl BUN")
                 ✓ Ilac/protokol adi, dozaj
                 ✓ Anatomik yapi, patogenez detayi
                 ✓ Ayirici tani kriteri, tedavi yontemi
                 ✓ Yem/cevre faktoru ile SPESIFIK metrik ("SNI 25 derecenin
                   uzerine ciktiginda yem tuketimi azalir")
                 -> kaynak GEREKLI.

   KURAL: Cumle "X bunlardan biri olabilir" / "Y bunlara dikkat etmeli" gibi
   GENEL bilgi veriyorsa filler. Eger cumle KAYNAKTAN bagimsiz olarak da
   dogru sayilabilecek genel-gecer bir ifade ise filler.

2) CHUNK_ID (sadece claim ise):
   - Bu iddia KAYNAKLAR'da hangi numaradaki kaynak tarafindan DOGRUDAN veya
     YAKIN paraphrase olarak destekleniyor?
   - **EMIN DEGILSEN**: chunk_id = null. Cumle drop edilir, bu daha guvenli.
     "Belki destekliyordur" yetmez — chunk'ta TANIMA, SAYI, ISIMLENDIRME
     fiilen geciyor mu kontrol et.
   - Sayisal iddialarda (örn "%5-25", "8-15 mg/dl") chunk'ta TAM o sayi/aralik
     gecmiyorsa chunk_id = null. Yakin baska sayi kabul edilmez.
   - Birden cok kaynak destekliyorsa, EN guclu destegi vereni sec.

3) EVIDENCE (sadece claim + chunk_id varsa):
   - O kaynak chunk'tan, iddiayi destekleyen KISA bir alinti (10-25 kelime)
     ver. KELIMESI KELIMESINE chunk'tan KOPYALA, parafraz etme.
   - Frontend bu alintiyi chunk icinde aratip highlight edecek.

KESINLIKLE JSON DON. Aciklama, markdown YOK. Format:
{{
  "sentences": [
    {{"idx": 1, "type": "claim",  "chunk_id": 2,    "evidence": "kaynaktan birebir alinti"}},
    {{"idx": 2, "type": "filler", "chunk_id": null, "evidence": null}},
    {{"idx": 3, "type": "claim",  "chunk_id": null, "evidence": null}},
    ...
  ]
}}

ONEMLI:
- Sira numarasi (idx) 1'den baslar, YANITTAKI cumle siralamasiyla ayni olmali.
- type="filler" ise chunk_id ve evidence MUTLAKA null.
- type="claim" ise chunk_id ya 1..{n_sources} arasi bir tam sayi YA DA null.
- chunk_id=null ise evidence de null.
- evidence verirken chunk'taki ifadenin tam halini kopyala (Turkce/Ingilizce
  fark etmez), uydurma."""


# ─────────────────────────────────────────────────────────────────
# JSON PARSE
# ─────────────────────────────────────────────────────────────────

def _parse_judge_json(raw: str, n_sentences: int, n_sources: int) -> list[dict] | None:
    """LLM raw output'undan {sentences: [...]} cek. None dondurursek hata."""
    # JSON blogu bul (LLM bazen ``` ile sarmaliyor)
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except Exception:
        return None
    sentences = data.get("sentences")
    if not isinstance(sentences, list):
        return None

    # idx -> entry haritala (LLM siralamayi bozarsa duzeltebilelim)
    by_idx: dict[int, dict] = {}
    for s in sentences:
        if not isinstance(s, dict):
            continue
        raw_idx = s.get("idx")
        if raw_idx is None:
            continue
        try:
            idx = int(raw_idx)
        except (TypeError, ValueError):
            continue
        if idx < 1 or idx > n_sentences:
            continue
        s_type = s.get("type")
        if s_type not in ("claim", "filler"):
            continue
        chunk_id = s.get("chunk_id")
        if chunk_id is not None:
            try:
                chunk_id = int(chunk_id)
            except Exception:
                chunk_id = None
            if chunk_id is not None and (chunk_id < 1 or chunk_id > n_sources):
                chunk_id = None
        if s_type == "filler":
            chunk_id = None
        evidence = s.get("evidence")
        if not isinstance(evidence, str) or chunk_id is None:
            evidence = None
        else:
            evidence = evidence.strip() or None
        by_idx[idx] = {
            "idx": idx, "type": s_type, "chunk_id": chunk_id,
            "evidence": evidence,
        }

    # Eksik idx'leri "claim, null chunk" (drop) olarak doldur — guvenli taraf
    out: list[dict] = []
    for i in range(1, n_sentences + 1):
        if i in by_idx:
            out.append(by_idx[i])
        else:
            out.append({
                "idx": i, "type": "claim", "chunk_id": None,
                "evidence": None, "missing": True,
            })
    return out


# ─────────────────────────────────────────────────────────────────
# EVIDENCE DOGRULAMA — judge'in chunk_id tahminini deterministik kontrol
# ─────────────────────────────────────────────────────────────────
#
# Sorun: LLM judge bazen claim'i dogru paragrafta yakaliyor ama yanlis chunk_id
# (1) veriyor — gercek kaynak baska bir chunktayken. Cozum: judge'in dondurdugu
# evidence alintisi gercekten hangi chunkta gectigini substring match ile bul.
#   - Evidence'in chunk_id chunk'unda gectigine bakilir → eslesirse onaylanir.
#   - Aksi halde tum chunklar taranir, evidence hangisinde gecerse o chunk
#     atanir (LLM'in tahmini overrride edilir).
#   - Hicbir chunkta yoksa chunk_id = null (drop) — evidence muhtemelen
#     halusinasyon.

# Turkce'ye/Ingilizce'ye duyarsiz, noktalama-agnostik karsilastirma icin normalize.
_WORD_RE = re.compile(r"[A-Za-zĞÜŞİÖÇğüşıöç0-9]+")


def _normalize(text: str) -> str:
    """Kucuk harfe cevir + bos olmayan word karakterlerini birlestir.
    Boylece 'E. coli, K99' ile 'E.coli K99' ayni kabul edilir."""
    return " ".join(w.lower() for w in _WORD_RE.findall(text))


# Token-overlap fallback icin stopword listesi — sadece evrensel filler.
# Tibbi terim BARINDIRMIYOR (kullanici talebi: scalable, hardcode tibbi sozluk YOK).
_STOPWORDS = frozenset({
    # TR
    "icin", "ile", "olan", "olur", "olabilir", "veya", "ya", "ama", "fakat",
    "ancak", "gibi", "kadar", "daha", "cok", "biraz", "her", "bir", "birden",
    "bunlar", "sunlar", "bunun", "sunu", "bunu", "burada", "orada", "olarak",
    "yer", "alir", "vardir", "yoktur", "kullanilir", "uygulanir", "yapilir",
    "olusur", "saglar", "neden", "nedenleri", "arasinda", "dolayisiyla",
    # EN
    "and", "the", "for", "with", "that", "this", "are", "was", "were", "have",
    "has", "had", "from", "their", "they", "them", "which", "these", "those",
    "such", "into", "over", "than", "also", "more", "less", "between", "among",
    "include", "includes", "including",
})


def _tokens_for_overlap(text: str) -> set[str]:
    """Token overlap karsilastirmasi icin: kucuk harf + 5+ karakter + stopword
    olmayan kelimeler. Rare/distinctive token'lar — ortak kelimelerin esleme
    skorunu bozmasini onler."""
    return {
        w.lower() for w in _WORD_RE.findall(text)
        if len(w) >= 5 and w.lower() not in _STOPWORDS
    }


def _find_chunk_for_evidence(
    evidence: str,
    chunks: list[dict],
    declared_id: int | None,
) -> tuple[int | None, str]:
    """Evidence'in fiilen hangi chunk'ta gectigini bul.

    Returns:
        (chunk_id, reason) — chunk_id None ise evidence hicbir yerde yok.
        reason: "confirmed" | "reassigned" | "not_found" | "skipped"
    """
    norm_ev = _normalize(evidence)
    if len(norm_ev) < 12:  # cok kisa evidence — guvenilmez, judge'a guven
        return declared_id, "skipped"

    norm_chunks = [_normalize(c.get("text", "")) for c in chunks]

    # 1) Tam normalize substring
    for i, nc in enumerate(norm_chunks, 1):
        if norm_ev in nc:
            if declared_id == i:
                return i, "confirmed"
            return i, "reassigned"

    # 2) Ilk 5-6 kelimelik onek ile dene (paraphrase tolerans)
    words = norm_ev.split()
    for win in range(min(6, len(words)), 3, -1):
        prefix = " ".join(words[:win])
        for i, nc in enumerate(norm_chunks, 1):
            if prefix in nc:
                if declared_id == i:
                    return i, "confirmed"
                return i, "reassigned"

    # 3) Token-overlap fallback: evidence cumlesini "rare token set"ine cevir,
    #    her chunk'in token set'i ile kesisim oranina bak. >=%50 ve >=2 token
    #    ortak ise o chunk kabul. Bu sayede evidence parafraze edilmis veya
    #    parcali yazilmis olsa bile (judge cumleyi yeniden kurmus olsa bile)
    #    dogru chunk yakalanabilir. Tibbi sozluk gerektirmez — saf IR mantigi.
    ev_tokens = _tokens_for_overlap(evidence)
    if len(ev_tokens) >= 2:
        best_idx = None
        best_overlap = 0
        best_ratio = 0.0
        for i, c in enumerate(chunks, 1):
            ch_tokens = _tokens_for_overlap(c.get("text", ""))
            inter = len(ev_tokens & ch_tokens)
            if inter > best_overlap:
                best_overlap = inter
                best_ratio = inter / len(ev_tokens)
                best_idx = i
        if best_idx is not None and best_overlap >= 2 and best_ratio >= 0.5:
            if declared_id == best_idx:
                return best_idx, "confirmed"
            return best_idx, "reassigned"

    # 4) Hicbir yerden eslesme yok → drop
    return None, "not_found"


def _verify_evidence(decisions: list[dict], chunks: list[dict]) -> None:
    """Hard-code substring/token verify — HIZLI ON KONTROL.

    chunk_id_judge: LLM'in ilk tahmini (debug icin saklanir)
    chunk_id_hardcode: substring verify sonrasi (yine debug)
    verify_reason: confirmed | reassigned | not_found | no_evidence | skipped

    NOT: chunk_id'yi hala set ediyoruz cunku LLM verifier hata verirse
    fallback olarak bu sonuc kullanilir. Normal akiste LLM verifier nihai
    karari override eder."""
    for d in decisions:
        if d.get("type") != "claim":
            continue
        declared = d.get("chunk_id")
        evidence = d.get("evidence")
        if not evidence:
            d["chunk_id_judge"] = declared
            d["chunk_id_hardcode"] = declared
            d["verify_reason"] = "no_evidence"
            continue
        new_id, reason = _find_chunk_for_evidence(evidence, chunks, declared)
        d["chunk_id_judge"] = declared
        d["chunk_id_hardcode"] = new_id
        d["chunk_id"] = new_id  # fallback degeri
        d["verify_reason"] = reason


# ─────────────────────────────────────────────────────────────────
# LLM EVIDENCE VERIFIER (2. asama — gpt-oss-120b reasoning=high)
# ─────────────────────────────────────────────────────────────────

VERIFIER_PROMPT = """Görev: Aşağıdaki her İDDİA için, KAYNAKLAR içinde o iddianın anlamını veren pasajı bul ve birebir kopyala.

Her İDDİA satırının sonunda judge'in ön tahmini var (chunk_id + önerdiği alıntı). Bunu doğrula ya da düzelt:
  - Önerilen alıntı gerçekten iddianın anlamını veriyorsa: o chunk_id ve alıntıyı onayla.
  - Önerilen alıntı iddiayı anlamca karşılamıyorsa: doğru pasajı KAYNAKLAR içinde ara, varsa ver.
  - Hiçbir kaynak iddianın anlamını vermiyorsa: chunk_id=null, quote=null.

Bu basit bir eşleşme işi. Yargı yok, yorum yok. Sadece "iddianın anlamı hangi cümlede geçiyor" sorusu.

İDDİALAR
(Her iddia iki satirdan olusur:
   "N. CLAIM: <iddia metni>"          ← degerlendirilecek cumle
   "   JUDGE_TAHMIN: chunk_id=X, evidence=\"...\""  ← judge'in on tahmini)
{claims_block}

KAYNAKLAR
{chunks_block}

EŞLEŞME KURALI (objektif)
- İddia ve pasaj aynı olguyu/durumu anlatmalı. Paraphrase, kelime sıralaması farkı kabul.
- Eşanlamlı terimler aynı sayılır: "E. coli" = "Escherichia coli", "ETEC" = "enterotoksijenik E. coli", "rotavirüs" = "rotavirus".
- Sayısal değerler farklı ifade edilebilir ama aynı gerçeği anlatmalı ("yarısından fazlası" ≈ "%53-57").
- İddia bir liste/şema ise (örn. yaş-patojen-dışkı tablosu), kaynakta aynı eşleşmenin geçtiği pasaj olmalı.
- İddianın ana terimleri/sayıları kaynakta YOK, sadece konu benzer ise: null. ("Aynı konu" yetmez.)

JSON ÇIKTI (yalnızca bu, hiçbir açıklama veya metin yok):
{{
  "verdicts": [
    {{"idx": 1, "chunk_id": 2, "quote": "kaynaktan birebir 10-25 kelime"}},
    {{"idx": 2, "chunk_id": null, "quote": null}}
  ]
}}

KURALLAR
- quote: kaynaktan birebir kopya, Türkçe karakterler (ş, ı, ğ, ç, ö, ü, İ) korunmalı, 10-25 kelime.
- chunk_id null ise quote da null.
- idx sırası İDDİALAR listesiyle aynı."""


def _build_verifier_prompt(decisions: list[dict], chunks: list[dict]) -> tuple[str, list[int]]:
    """Verifier prompt'unu hazirlar. Donen ikinci deger: (claim_idx -> sentence_idx)
    haritasi — verifier'a verilen 1-indexed sira ile decisions[i]['idx'] eslesmesi.

    Her claim satirina judge'in on tahmini (chunk_id + evidence) hint olarak eklenir.
    Boylece verifier'in gorevi "sifirdan arama" degil "tahmini dogrula veya duzelt"
    haline gelir — Gemini Flash gibi orta seviye modeller icin cok daha kolay gorev."""
    claim_lines: list[str] = []
    sentence_idx_map: list[int] = []
    for d in decisions:
        if d.get("type") != "claim":
            continue
        sentence_idx_map.append(d["idx"])
        claim_idx = len(sentence_idx_map)  # 1-indexed verifier'a giden
        text = (d.get("text") or "").strip().replace("\n", " ")
        # Judge'in on tahmini — verifier dogrulayacak veya duzeltecek.
        # NOT: Bu noktada d["chunk_id"] hardcode tarafindan zaten override edilmis
        # olabilir (verify_reason="reassigned" durumu). En guvenilir hint icin
        # hardcode-sonrasi degeri kullaniyoruz.
        #
        # Format: CLAIM ve JUDGE ayri satirlarda — tek satirda " || " ayraci ile
        # birlestirmek Claude Sonnet'te "claim metni bos" yanilgisini tetikledi.
        hint_cid = d.get("chunk_id")
        hint_ev = (d.get("evidence") or "").strip().replace("\n", " ")
        if hint_cid is not None and hint_ev:
            hint_ev_short = hint_ev[:200]
            judge_line = f'   JUDGE_TAHMIN: chunk_id={hint_cid}, evidence="{hint_ev_short}"'
        else:
            judge_line = "   JUDGE_TAHMIN: yok"
        claim_lines.append(f"{claim_idx}. CLAIM: {text}\n{judge_line}")

    chunk_lines: list[str] = []
    for i, c in enumerate(chunks[:5], 1):
        title = (c.get("metadata") or {}).get("source_title", "?")
        text = (c.get("text") or "").strip()
        chunk_lines.append(f"[Kaynak {i}] {title}\n{text}")

    prompt = VERIFIER_PROMPT.format(
        claims_block="\n".join(claim_lines) if claim_lines else "(claim yok)",
        chunks_block="\n\n".join(chunk_lines) if chunk_lines else "(kaynak yok)",
    )
    return prompt, sentence_idx_map


def _parse_verifier_json(raw: str, n_claims: int, n_chunks: int) -> list[dict] | None:
    """Verifier JSON ciktisini parse et. Beklenen format (v2 — quote-first):
        {"verdicts": [{"idx": int, "chunk_id": int|null, "quote": str|null}, ...]}

    "supported" boolean kaldirildi — chunk_id != null ise supported sayilir.
    Boylelikle model tembel "default false" cevabi yerine extraction gorevine
    odaklanir.

    Geriye uyumluluk: eski "claims" anahtari da kabul edilir."""
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except Exception:
        return None
    # Yeni format "verdicts", eski format "claims" — ikisi de kabul
    items = data.get("verdicts") or data.get("claims")
    if not isinstance(items, list):
        return None

    by_idx: dict[int, dict] = {}
    for it in items:
        if not isinstance(it, dict):
            continue
        raw_idx = it.get("idx")
        if raw_idx is None:
            continue
        try:
            idx = int(raw_idx)
        except (TypeError, ValueError):
            continue
        if idx < 1 or idx > n_claims:
            continue

        chunk_id = it.get("chunk_id")
        if chunk_id is not None:
            try:
                chunk_id = int(chunk_id)
            except (TypeError, ValueError):
                chunk_id = None
            if chunk_id is not None and (chunk_id < 1 or chunk_id > n_chunks):
                chunk_id = None

        # supported = chunk_id null degilse true (derived)
        supported = chunk_id is not None

        # Quote: yeni format "quote", eski "verbatim_passage"
        passage = it.get("quote") or it.get("verbatim_passage")
        if not isinstance(passage, str) or not passage.strip() or chunk_id is None:
            passage = None
        else:
            passage = passage.strip()

        by_idx[idx] = {
            "idx": idx,
            "supported": supported,
            "chunk_id": chunk_id,
            "verbatim_passage": passage,
        }

    out: list[dict] = []
    for i in range(1, n_claims + 1):
        if i in by_idx:
            out.append(by_idx[i])
        else:
            out.append({
                "idx": i, "supported": False, "chunk_id": None,
                "verbatim_passage": None, "missing": True,
            })
    return out


def _verify_evidence_with_llm(
    decisions: list[dict],
    chunks: list[dict],
) -> tuple[str, str | None]:
    """LLM (Llama 4 Scout @ Groq) ile decisions'i IN-PLACE override eder.

    Her CLAIM icin nihai chunk_id ve verbatim_passage ayarlanir. Hata olursa
    hardcode sonucuna geri dusulur (chunk_id_hardcode kullanilir).

    Returns:
        (raw_response, error). Hata yoksa error=None."""
    claims = [d for d in decisions if d.get("type") == "claim"]
    if not claims:
        return "", None
    if not chunks:
        return "", None

    prompt, sentence_idx_map = _build_verifier_prompt(decisions, chunks)
    n_claims = len(sentence_idx_map)
    n_chunks = min(len(chunks), 5)

    raw_response = ""
    err = None
    try:
        llm = _get_verifier_llm()
        max_retries = 1
        for attempt in range(max_retries + 1):
            try:
                resp = llm.invoke([{"role": "user", "content": prompt}])
                raw_response = str(resp.content).strip()
                break
            except Exception as rate_err:
                msg = str(rate_err)
                if attempt >= max_retries:
                    raise
                if "rate_limit" not in msg.lower() and "429" not in msg:
                    raise
                m = re.search(r"try again in ([\d.]+)s", msg)
                wait_s = float(m.group(1)) + 2.0 if m else 5.0
                print(f"[verifier] rate limit, {wait_s:.1f}s bekle")
                time.sleep(wait_s)
    except Exception as e:
        err = str(e)[:300]
        print(f"[verifier] LLM hata: {err}")

    if err or not raw_response:
        # Hata: hardcode sonucu nihai karar olur (zaten chunk_id'de saklı)
        for d in decisions:
            if d.get("type") != "claim":
                continue
            d["verifier_status"] = "llm_error"
        return raw_response, err

    parsed = _parse_verifier_json(raw_response, n_claims, n_chunks)
    if parsed is None:
        print(f"[verifier] JSON parse fail")
        for d in decisions:
            if d.get("type") != "claim":
                continue
            d["verifier_status"] = "parse_error"
        return raw_response, "JSON parse failed"

    # Verifier sonuclarini decisions'a uygula (sentence_idx_map ile eslestir)
    for verifier_item, sentence_idx in zip(parsed, sentence_idx_map):
        # decisions[i].idx == sentence_idx olan kaydi bul
        target = next((d for d in decisions if d.get("idx") == sentence_idx), None)
        if target is None:
            continue
        if verifier_item.get("missing"):
            target["verifier_status"] = "missing_from_llm"
            # Guvenli taraf: hardcode sonucunu koru (chunk_id zaten oradan geldi)
            continue
        target["verifier_status"] = "supported" if verifier_item["supported"] else "not_supported"
        target["chunk_id"] = verifier_item["chunk_id"]  # NIHAI karar
        if verifier_item["verbatim_passage"]:
            # evidence alanini verbatim pasajla degistir (eski yargi evidence'i atılır)
            target["evidence"] = verifier_item["verbatim_passage"]

    return raw_response, None


# ─────────────────────────────────────────────────────────────────
# REASSEMBLE
# ─────────────────────────────────────────────────────────────────

def _reassemble(decisions: list[dict], sentences: list[str]) -> str:
    """Kept cumleleri orijinal sira ile birlestir. Claim cumle sonuna [Kaynak N].

    Cumleler arasi orijinal newline yapisini elimizden geldigince koru:
    - List/bullet satiri ise kendi satirinda kalir
    - Normal cumleler ardisik ise tek satirda birlesir
    """
    kept_lines: list[str] = []
    for d, text in zip(decisions, sentences):
        keep = (d["type"] == "filler") or (d.get("chunk_id") is not None)
        if not keep:
            continue
        out = text.rstrip()
        if d["type"] == "claim" and d.get("chunk_id"):
            # Inline citation — frontend tiklanabilir hale getirecek
            if not out.endswith((".", "!", "?", ":", ";")):
                out = out + "."
            out = f"{out} [Kaynak {d['chunk_id']}]"
        # Bullet/numbered ise yeni satira
        if re.match(r"^\s*(\*\*|[-*]|\d+\.)", out):
            kept_lines.append(out)
        else:
            if kept_lines and not re.match(r"^\s*(\*\*|[-*]|\d+\.)", kept_lines[-1]):
                kept_lines[-1] = kept_lines[-1] + " " + out
            else:
                kept_lines.append(out)
    return "\n".join(kept_lines)


# ─────────────────────────────────────────────────────────────────
# FALLBACK MESAJLARI
# ─────────────────────────────────────────────────────────────────

_SAFE_FALLBACK_PRODUCER = (
    "Bu konuda elimdeki kaynaklarda yeterli bilgi bulamadim. "
    "Lutfen veteriner hekiminize danisin.\n\n"
    "⚠️ Bu bilgi karar destegidir."
)

_SAFE_FALLBACK_VET = (
    "Elimdeki kaynaklarda bu konuda spesifik bir bilgi dogrulanamadi. "
    "Lutfen guncel veteriner literaturune basvurun."
)


# ─────────────────────────────────────────────────────────────────
# NODE
# ─────────────────────────────────────────────────────────────────

def claim_attribution_node(state: dict) -> dict:
    """Per-claim citation attribution (Llama-3.3-70B judge)."""
    t0 = time.perf_counter()
    draft = state.get("draft_response", "")
    docs = state.get("retrieved_docs", [])
    user_role = state.get("user_role", "producer")

    # ── Skip durumlari ─────────────────────────────────────────
    if state.get("response_status") == "fallback":
        audit_log(state, "claim_attr_skip", reason="Generator fallback metni")
        trace_node(state, "claim_attribution",
                   input={"reason": "skip", "draft": trim_text(draft, 200)},
                   output={"skipped": True, "reason": "Generator fallback metni"})
        return state

    if not draft or len(draft) < 60:
        audit_log(state, "claim_attr_skip", reason="Yanit cok kisa")
        trace_node(state, "claim_attribution",
                   input={"reason": "skip", "draft": draft},
                   output={"skipped": True, "reason": "Yanit cok kisa"})
        return state

    if not docs:
        audit_log(state, "claim_attr_skip", reason="Kaynak yok")
        trace_node(state, "claim_attribution",
                   input={"reason": "skip"},
                   output={"skipped": True, "reason": "Kaynak yok"})
        return state

    # ── Generator artik atiflarini temizle (asla bizim formata uymaz) ───
    draft = _strip_generator_citations(draft)
    state["draft_response"] = draft  # asagidaki passthrough yollari icin

    # ── Cumleleri bol ──────────────────────────────────────────
    sentences = _split_sentences(draft)
    if not sentences:
        audit_log(state, "claim_attr_skip", reason="0 cumle parse edildi")
        trace_node(state, "claim_attribution",
                   input={"draft_in": trim_text(draft)},
                   output={"skipped": True, "reason": "0 cumle"})
        return state

    # ── Prompt'u kur ──────────────────────────────────────────
    sources_block = "\n\n".join(
        f"[Kaynak {i+1}] {d.get('metadata', {}).get('source_title', '?')}\n"
        f"{d.get('text', '').strip()[:1800]}"
        for i, d in enumerate(docs[:5])
    )
    sentences_block = "\n".join(f"{i+1}. {s}" for i, s in enumerate(sentences))

    prompt = JUDGE_PROMPT.format(
        sources=sources_block,
        sentences=sentences_block,
        n_sources=min(len(docs), 5),
    )

    # ── LLM cagrisi (1 retry rate-limit icin) ─────────────────
    raw_response = ""
    judge_error = None
    try:
        llm = _get_judge_llm()
        max_retries = 1
        for attempt in range(max_retries + 1):
            try:
                resp = llm.invoke([{"role": "user", "content": prompt}])
                raw_response = str(resp.content).strip()
                break
            except Exception as rate_err:
                msg = str(rate_err)
                if attempt >= max_retries:
                    raise
                if "rate_limit" not in msg.lower() and "429" not in msg:
                    raise
                m = re.search(r"try again in ([\d.]+)s", msg)
                wait_s = float(m.group(1)) + 2.0 if m else 10.0
                print(f"[claim_attr] rate limit, {wait_s:.1f}s bekle")
                time.sleep(wait_s)
    except Exception as e:
        judge_error = str(e)[:300]
        print(f"[claim_attr] LLM hata: {judge_error}")

    if judge_error or not raw_response:
        # LLM basarisiz — yaniti olduğu gibi birak (drop yapma)
        audit_log(state, "claim_attr_llm_error", reason=judge_error or "empty response")
        trace_node(state, "claim_attribution",
                   input={"draft_in": trim_text(draft),
                          "prompt": trim_text(prompt, 3000)},
                   output={"error": judge_error, "raw_response": trim_text(raw_response, 500),
                           "skipped": True, "action": "passthrough"},
                   latency_ms=(time.perf_counter() - t0) * 1000)
        state["grounding_action"] = "passthrough_error"
        return state

    # ── Parse ─────────────────────────────────────────────────
    decisions = _parse_judge_json(raw_response, len(sentences), min(len(docs), 5))
    if decisions is None:
        audit_log(state, "claim_attr_parse_error", reason="JSON parse failed")
        trace_node(state, "claim_attribution",
                   input={"draft_in": trim_text(draft),
                          "prompt": trim_text(prompt, 3000)},
                   output={"error": "JSON parse failed",
                           "raw_response": trim_text(raw_response, 2000),
                           "skipped": True, "action": "passthrough"},
                   latency_ms=(time.perf_counter() - t0) * 1000)
        state["grounding_action"] = "passthrough_parse_error"
        return state

    # ── 1. Hardcode evidence dogrulamasi (substring + token overlap) ──
    # Hizli ve deterministik. Chunk_id_hardcode set edilir, fallback degeri.
    _verify_evidence(decisions, docs[:5])

    n_hc_reassigned = sum(1 for d in decisions if d.get("verify_reason") == "reassigned")
    n_hc_not_found = sum(1 for d in decisions if d.get("verify_reason") == "not_found")

    # ── 2. LLM verifier (Opus / Sonnet / Gemini ...) — opsiyonel ─────
    # VERIFIER_ENABLED=False oldugunda atlanir. Nihai chunk_id ve evidence
    # hardcode asamasindaki degerlerden gelir (judge + substring verify).
    if VERIFIER_ENABLED:
        t_verify = time.perf_counter()
        verifier_raw, verifier_error = _verify_evidence_with_llm(decisions, docs[:5])
        verifier_ms = (time.perf_counter() - t_verify) * 1000
        n_verifier_supported = sum(1 for d in decisions
                                    if d.get("type") == "claim" and d.get("verifier_status") == "supported")
        n_verifier_not_supported = sum(1 for d in decisions
                                        if d.get("type") == "claim" and d.get("verifier_status") == "not_supported")
        n_verifier_errors = sum(1 for d in decisions
                                 if d.get("type") == "claim" and d.get("verifier_status") in ("llm_error", "parse_error", "missing_from_llm"))
        print(
            f"[claim_attr] hardcode: reassigned={n_hc_reassigned} not_found={n_hc_not_found} | "
            f"verifier ({verifier_ms:.0f}ms): supported={n_verifier_supported} "
            f"not_supported={n_verifier_not_supported} errors={n_verifier_errors}"
        )
    else:
        # Verifier kapali: hardcode sonucu nihai. verifier_status'u "disabled" yap
        # debug ekraninda gorunmesi icin, istatistikleri sifirla.
        verifier_raw, verifier_error = "", None
        verifier_ms = 0.0
        n_verifier_supported = 0
        n_verifier_not_supported = 0
        n_verifier_errors = 0
        for d in decisions:
            if d.get("type") == "claim":
                d["verifier_status"] = "disabled"
        print(
            f"[claim_attr] hardcode: reassigned={n_hc_reassigned} not_found={n_hc_not_found} | "
            f"verifier: DISABLED (hardcode sonucu nihai)"
        )

    # ── Decisions'i sentence text ile birlestir ──────────────
    annotated: list[dict] = []
    for d, text in zip(decisions, sentences):
        keep = (d["type"] == "filler") or (d.get("chunk_id") is not None)
        annotated.append({
            "idx": d["idx"],
            "text": text,
            "type": d["type"],
            "chunk_id": d.get("chunk_id"),  # NIHAI — verifier override etti
            "chunk_id_judge": d.get("chunk_id_judge"),  # Aşama 1 LLM tahmini
            "chunk_id_hardcode": d.get("chunk_id_hardcode"),  # Hardcode substring sonucu
            "verify_reason": d.get("verify_reason"),  # Hardcode reason
            "verifier_status": d.get("verifier_status"),  # Aşama 2 LLM kararı
            "evidence": d.get("evidence"),  # Verifier'in verbatim pasaji (override edildi)
            "supported": keep,
            "missing_from_llm": d.get("missing", False),
        })

    n_claims = sum(1 for a in annotated if a["type"] == "claim")
    n_filler = sum(1 for a in annotated if a["type"] == "filler")
    n_dropped = sum(1 for a in annotated if not a["supported"])
    n_kept = len(annotated) - n_dropped
    drop_ratio = n_dropped / max(n_claims, 1)  # filler hesaba katma

    print(
        f"[claim_attr] {len(annotated)} cumle: claim={n_claims} filler={n_filler} "
        f"kept={n_kept} dropped={n_dropped} drop_ratio={drop_ratio:.2f}"
    )

    cleaned = _reassemble(decisions, sentences)

    stats = {
        "total": len(annotated),
        "claims": n_claims,
        "filler": n_filler,
        "kept": n_kept,
        "dropped": n_dropped,
        "drop_ratio": round(drop_ratio, 3),
        "n_sources": min(len(docs), 5),
        # Hardcode (asama 1.5) verify istatistikleri — debug icin
        "verify_reassigned": n_hc_reassigned,
        "verify_dropped_evidence_missing": n_hc_not_found,
        # LLM verifier (asama 2) istatistikleri — nihai karar
        "verifier_supported": n_verifier_supported,
        "verifier_not_supported": n_verifier_not_supported,
        "verifier_errors": n_verifier_errors,
        "verifier_latency_ms": round(verifier_ms, 1),
    }
    latency_ms = (time.perf_counter() - t0) * 1000

    # ── RESCUE: retrieval cok guclu ama judge HER claim'i dropladi ──
    # rerank_top yuksekse (>=0.85) kaynaklar konuyla ACIKCA ilgili demektir.
    # Judge'in hicbir claim'i baglayamamasi bu durumda genelde judge varyansidir
    # (temp=0 olsa da MoE model run-to-run oynuyor), gercek bilgi yoklugu degil.
    # "Elimde bilgi yok" demek yerine generator taslagini oldugu gibi gecir.
    # Tradeoff: inline [Kaynak N] atifi olmaz (baglanan claim yok), ama alttaki
    # kaynak paneli yine gosterilir. Yalnizca TUM claim'ler droplandiginda devreye
    # girer — kismi drop'ta eski safe_fallback davranisi korunur.
    RESCUE_RERANK_THRESHOLD = 0.85
    rerank_top = float(state.get("rerank_top_score", 0.0))
    all_claims_dropped = n_claims >= 1 and not any(
        a["type"] == "claim" and a["supported"] for a in annotated
    )
    if all_claims_dropped and rerank_top >= RESCUE_RERANK_THRESHOLD:
        state["draft_response"] = draft  # generator taslagi (atifsiz) korunur
        state["grounding_action"] = "passthrough_strong_retrieval"
        audit_log(state, "claim_attr_passthrough_strong_retrieval",
                  reason=f"rerank_top={rerank_top:.2f} >= {RESCUE_RERANK_THRESHOLD}, "
                         f"judge tum {n_claims} claim'i dropladi -> taslak gecirildi")
        print(
            f"[claim_attr] RESCUE: rerank_top={rerank_top:.2f} yuksek, judge tum "
            f"{n_claims} claim'i dropladi -> passthrough (atifsiz)"
        )
        trace_node(state, "claim_attribution",
                   input={"draft_in": trim_text(draft),
                          "prompt": trim_text(prompt, 3000),
                          "n_sources": min(len(docs), 5)},
                   output={"sentences": annotated, "stats": stats,
                           "raw_response": trim_text(raw_response, 2000),
                           "action": "passthrough_strong_retrieval",
                           "rerank_top": round(rerank_top, 4),
                           "draft_out": draft,
                           "judge": "meta-llama/llama-3.3-70b-instruct"},
                   latency_ms=latency_ms)
        return state

    # ── Cogu claim drop -> safe fallback ──────────────────────
    if n_claims >= 3 and drop_ratio > 0.6:
        fallback = _SAFE_FALLBACK_PRODUCER if user_role == "producer" else _SAFE_FALLBACK_VET
        state["draft_response"] = fallback
        state["grounding_action"] = "safe_fallback"
        audit_log(state, "claim_attr_safe_fallback",
                  reason=f"drop_ratio={drop_ratio:.2f} of {n_claims} claims")
        trace_node(state, "claim_attribution",
                   input={"draft_in": trim_text(draft),
                          "prompt": trim_text(prompt, 3000),
                          "n_sources": min(len(docs), 5)},
                   output={"sentences": annotated, "stats": stats,
                           "raw_response": trim_text(raw_response, 2000),
                           "verifier_raw_response": trim_text(verifier_raw, 2000),
                           "verifier_error": verifier_error,
                           "action": "safe_fallback", "draft_out": fallback,
                           "judge": "meta-llama/llama-3.3-70b-instruct",
                           "verifier": ("anthropic/claude-opus-4-8" if VERIFIER_ENABLED else "DISABLED")},
                   latency_ms=latency_ms)
        return state

    if not cleaned.strip():
        fallback = _SAFE_FALLBACK_PRODUCER if user_role == "producer" else _SAFE_FALLBACK_VET
        state["draft_response"] = fallback
        state["grounding_action"] = "safe_fallback_empty"
        audit_log(state, "claim_attr_safe_fallback", reason="empty after filter")
        trace_node(state, "claim_attribution",
                   input={"draft_in": trim_text(draft),
                          "prompt": trim_text(prompt, 3000),
                          "n_sources": min(len(docs), 5)},
                   output={"sentences": annotated, "stats": stats,
                           "raw_response": trim_text(raw_response, 2000),
                           "verifier_raw_response": trim_text(verifier_raw, 2000),
                           "verifier_error": verifier_error,
                           "action": "safe_fallback_empty", "draft_out": fallback,
                           "judge": "meta-llama/llama-3.3-70b-instruct",
                           "verifier": ("anthropic/claude-opus-4-8" if VERIFIER_ENABLED else "DISABLED")},
                   latency_ms=latency_ms)
        return state

    state["draft_response"] = cleaned
    state["grounding_action"] = "filtered" if n_dropped > 0 else "passed"
    audit_log(state, "claim_attr_done",
              reason=f"action={state['grounding_action']}, "
                     f"claims={n_claims} filler={n_filler} dropped={n_dropped}")
    trace_node(state, "claim_attribution",
               input={"draft_in": trim_text(draft),
                      "prompt": trim_text(prompt, 3000),
                      "n_sources": min(len(docs), 5)},
               output={"sentences": annotated, "stats": stats,
                       "raw_response": trim_text(raw_response, 2000),
                       "verifier_raw_response": trim_text(verifier_raw, 2000),
                       "verifier_error": verifier_error,
                       "action": state["grounding_action"],
                       "draft_out": cleaned,
                       "judge": "meta-llama/llama-3.3-70b-instruct",
                       "verifier": ("anthropic/claude-opus-4-8" if VERIFIER_ENABLED else "DISABLED")},
               latency_ms=latency_ms)
    return state
