"""
PaytarAI — Critic Node (Hibrit)

Taslak yaniti iki katmanli denetler:
1) Hard rules (regex/keyword): yasak ilac+doz, Latince terim, markdown tablo,
   inline citation, numerical halusinasyon
2) LLM-judge (Cerebras gpt-oss-120b low reasoning): semantik kontroller —
   disclaimer varligi, acil uyari uygunlugu, semantik halusinasyon, sade dil
"""

import json
import re

from langchain_openai import ChatOpenAI

from app.config import settings
from app.graph.audit import audit_log


# ---------------------------------------------------------------
# SANITIZE — kozmetik sorunlari LLM cagirmadan temizler
# ---------------------------------------------------------------

_INLINE_CITATION_PATTERNS = [
    r"【\s*Kaynak\s*\d+\s*】",
    r"\[\s*Kaynak\s*\d+\s*\]",
    r"\(\s*Kaynak\s*\d+\s*\)",
    r"【\s*Referans\s*\d+\s*】",
    r"\[\s*Referans\s*\d+\s*\]",
]

_META_PHRASES = [
    "kaynakta doğrudan tedavi önerisi yoktur, sadece tanısal ilişki verilmiştir",
    "kaynakta doğrudan tedavi önerisi yoktur",
    "kaynakta yalnızca tanısal ilişki verilmiştir",
    "kaynaklarda detay yok",
    "kaynakta detay yok",
    "tabloda görüldüğü gibi",
    "tabloda görüldüğü üzere",
    "kaynakta belirtilmemiş",
]


def _sanitize_draft(draft: str, user_role: str) -> str:
    """Kozmetik sorunlari LLM olmadan duzeltir."""
    cleaned = draft

    # 1. Inline [Kaynak N] / 【Kaynak N】 etiketlerini sil (her iki rol icin)
    for pat in _INLINE_CITATION_PATTERNS:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)

    # 2. Meta-yorum cumlelerini sil (vet & uretici)
    for phrase in _META_PHRASES:
        cleaned = re.sub(re.escape(phrase) + r"[.,;]?\s*", "", cleaned, flags=re.IGNORECASE)

    # 3. Uretici modunda kaynak satirini ve "Rebhun's" gibi kitap adlarini sil
    if user_role == "producer":
        # "Kaynak: ..." satirini tamamen sil
        cleaned = re.sub(r"(?im)^\s*Kaynak\s*[:：].*$", "", cleaned)
        cleaned = re.sub(r"(?im)^\s*Referans\s*[:：].*$", "", cleaned)
        # Cumle icinde gecen kitap adlarini sil
        cleaned = re.sub(r"Rebhun'?s?[^,.\n]*", "", cleaned, flags=re.IGNORECASE)

    # 4. Cift bosluklari ve fazla bos satirlari topla
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = cleaned.strip()

    return cleaned


# Critic kontrol fonksiyonlari

def _check_source_citation(draft: str, docs: list[dict], user_role: str = "veterinarian") -> str | None:
    """Vet: sonda kaynak atfi gereklidir. Uretici: bu kontrol gecerli degil (sanitize halleder)."""
    if user_role == "producer":
        return None

    # Vet — sondaki kaynak satiri gereklidir; inline/meta sanitize'da temizlendi
    citation_markers = ["kaynak:", "kaynak :", "source:", "referans:"]
    has_citation = any(marker in draft.lower() for marker in citation_markers)
    if not has_citation and docs:
        return "Yanitin sonunda kaynak atfi yok. Sonuna tek satir 'Kaynak: [Kitap Adi], bolum' ekle."
    return None


def _check_hallucination(draft: str, docs: list[dict]) -> str | None:
    """
    DAR halusinasyon kontrolu — sadece ILAÇ DOZ sayilari (mg/kg, ml/kg, iu/kg gibi).

    Eskiden tum sayilari kontrol ediyordu (10 dk, 38°C, 500 ml dahil) → bu
    genel bakim tavsiyelerini halusinasyon sandi (false positive). Yeni mantik:
    sadece <SAYI> + <BIRIM>/<VUCUT_AGIRLIK_BIRIMI> kalibinda gelen DOZ sayilari.

    Genel sure/sicaklik/hacim sayilari (10 dk, 38°C, 500 mL gibi) artik denetlenmez —
    bunlar genel bakim onerileri, kaynakta birebir olmasi gerekmez.
    """
    # Doz kalibi: 10 mg/kg, 5 ml/kg, 25 iu/kg, 0.5 mg/saat, vb.
    dose_pattern = re.compile(
        r"\b(\d+(?:\.\d+)?)\s*(?:mg|ml|mcg|iu|cc|g)\s*/\s*(?:kg|gun|day|saat|h|hr)\b",
        re.IGNORECASE,
    )

    def extract_doses(text: str) -> set[float]:
        return {float(m) for m in dose_pattern.findall(text)}

    if not docs:
        return None

    draft_doses = extract_doses(draft)
    if not draft_doses:
        return None  # Doz yoksa kontrol gerek yok

    source_text = " ".join(d.get("text", "") for d in docs)
    source_doses = extract_doses(source_text)

    # Her draft dozu icin kaynakta %10 toleransla yakin deger var mi
    suspicious: list[str] = []
    for num in draft_doses:
        found = False
        for src_num in source_doses:
            if src_num == 0:
                continue
            if abs(num - src_num) / src_num < 0.10:
                found = True
                break
        if not found:
            suspicious.append(str(num))

    # 2'den fazla eslesmeyen doz → reddet (kalibre)
    if len(suspicious) > 2:
        return f"Yanitta {len(suspicious)} DOZ degeri kaynaklarda dogrulanamadi: {suspicious[:3]}. Kaynakta olmayan doz uydurma."

    return None


def _check_role_compliance(draft: str, user_role: str) -> str | None:
    """Rol bazli uyumluluk kontrolu."""
    if user_role == "producer":
        # Uretici modunda receteli ilac, dozaj veya teknik terim olmamali
        prescription_markers = [
            # Dozaj birimleri
            "mg/kg", "ml/kg", "mg/ml", "iu/kg", "mg/gün", "ml/gün",
            # Uygulama yollari (EN)
            "iv ", "i.v.", "intramuscular", "subcutaneous", "intravenous", "intramammary",
            # Uygulama yollari (TR)
            "intravenöz", "intramüsküler", "subkütan", "kas içi enjeksiyon", "damar içi enjeksiyon",
            # Receteli ilac adlari
            "penisilin", "penicillin", "oksitetrasiklin", "oxytetracycline",
            "ampisilin", "ampicillin", "deksametazon", "dexamethasone",
            "flunixin", "meloksikem", "meloxicam",
            # Karmasik tibbi terimler / Latince
            "peritonitis", "endometritis", "septisemi", "septik şok",
            "musculoskeletal", "polyarthritis", "hipokalsemi", "hipomagnezemi",
            "recumbency", "palpasyon", "primiparous", "multiparous",
            "anoreksi", "subinvolüsyon", "ruminal tympani", "asidoz", "ketozis",
        ]
        violations = [m for m in prescription_markers if m in draft.lower()]
        if violations:
            return f"Uretici modunda teknik dozaj/uygulama/ilac/tibbi terim kullanildi: {violations}. Sade Turkce ile yeniden yaz, tibbi terim parantez icinde bile yazma."

        # Tablo (markdown) yasak — uretici tablo gormez
        # En az 2 satir | ile basliyorsa veya | ... | --- ... --- | kalibi varsa tablo say
        lines_with_pipe = [ln for ln in draft.splitlines() if ln.strip().startswith("|") and "|" in ln.strip()[1:]]
        if len(lines_with_pipe) >= 2:
            return "Uretici yanitinda tablo kullanildi. Tablo yerine 2-3 cumlelik sade aciklama yaz."

    elif user_role == "veterinarian":
        # Veteriner modunda cok basit dil kontrolu (istege bagli)
        pass

    return None


def _check_emergency_flag(draft: str, docs: list[dict]) -> str | None:
    """Acil durumlar icin uyari kontrolu."""
    # Sadece gercekten hayati tehlike belirten terimler
    emergency_keywords = [
        "fatal", "death", "emergency", "life-threatening",
    ]

    source_text = " ".join(d["text"] for d in docs).lower()
    source_has_emergency = any(kw in source_text for kw in emergency_keywords)

    # Yanittaki acil uyari varyantlari
    draft_lower = draft.lower()
    warning_markers = ["acil", "hemen veteriner", "hayati tehlike", "tehlike", "uyarı"]
    draft_has_warning = any(m in draft_lower for m in warning_markers)

    if source_has_emergency and not draft_has_warning:
        return "Kaynaklar acil/tehlikeli durum belirtiyor ancak yanit acil uyari icermiyor. ACİL uyarisi ekle."

    return None


def _check_disclaimer(draft: str, user_role: str) -> str | None:
    """[ESKI — LLM-judge'a devredildi] Uretici modunda zorunlu disclaimer kontrolu.

    Bu fonksiyon artik critic_node'dan cagrilmaz. Kalmasinin tek sebebi
    backward compat — yeni karar LLM-judge tarafindan veriliyor.
    """
    if user_role == "producer":
        disclaimer_markers = ["karar destegi", "veteriner hekime danisin", "veteriner", "disclaimer"]
        has_disclaimer = any(m in draft.lower() for m in disclaimer_markers)
        if not has_disclaimer:
            return "Uretici modunda zorunlu disclaimer eksik. Yanitinin sonuna uyari ekle."
    return None


# ---------------------------------------------------------------
# LLM-JUDGE — sade stil kontrolleri (Cerebras gpt-oss-120b, low reasoning)
#
# Notlar:
# - Halusinasyon kontrolu kaldirildi (kaynak metin gondermiyoruz).
#   Halusinasyon icin: numerical hard rule + eval fact_coverage_llm kullaniliyor.
# - Judge SADECE yanitin ic tutarliligini kontrol eder: disclaimer, emergency, sade dil.
# - Kaynak metin GONDERILMIYOR — token tasarrufu + judge'in yanlis "kaynakta yok"
#   reflexini onler.
# ---------------------------------------------------------------

JUDGE_PROMPT = """Sen bir veteriner asistan yaniti degerlendiriyorsun. Asagidaki yaniti 5 boyutta degerlendir ve SADECE JSON cevap ver.

KULLANICI ROLU: {user_role}
ACIL DURUM SINYALI VAR MI (kaynakta "fatal/death/emergency" gectiyse "true"): {source_has_emergency}

KULLANICININ SORUSU:
\"\"\"
{user_query}
\"\"\"

KAYNAK METINLER (yanit bu metinlere dayanmali):
\"\"\"
{sources}
\"\"\"

DEGERLENDIRILECEK YANIT:
\"\"\"
{draft}
\"\"\"

JSON cevabin TAM olarak su yapida olmali:

{{
  "disclaimer_present": <true/false>,
  "emergency_appropriate": <true/false>,
  "lay_language_ok": <true/false>,
  "grounded": <true/false>,
  "answer_relevant": <true/false>
}}

ALAN ACIKLAMALARI:
- disclaimer_present: user_role=producer ise yanitta "veteriner/veterinerinize/uzmana danisin" gibi bir yonlendirme var mi (paraphrase, "uzman", "doktor" gibi kelimeler de OK). user_role=veterinarian ise her zaman true don.
- emergency_appropriate: user_role=veterinarian ise her zaman true don (vet uzmandir, 🚨 emoji'si gerekmez). user_role=producer VE ACIL SINYALI VAR ise yanitta acil uyarisi ("ACIL", "🚨", "hemen veteriner", "tehlike", "acil arayin", "vakit kaybetme") var mi? Producer + ACIL SINYALI YOK ise her zaman true don.
- lay_language_ok: user_role=producer ise yanit sade Turkce mi? "Mastitis", "ketozis", "hipokalsemi", "recumbency" gibi Latince/teknik terimler CIPLAK (parantez icinde aciklama olmadan) kullanilmis mi? Eger Turkce karsiligi parantez icinde varsa (orn. "meme iltihabi (mastitis)") sorun yok, TRUE don. Sadece tum yaniti tibbi jargonla dolu ise FALSE don. user_role=veterinarian ise her zaman true don.
- grounded: Yanittaki SPESIFIK iddialar (sayilar, ilac/marka adi, dozaj, satin alma yeri, belirli protokol adimi, patogenez detayi) yukaridaki KAYNAK METINLER'de DOGRUDAN veya yakin paraphrase olarak gecmis mi? TRUE don eger: (a) Yanit cogunlukla genel oneri/kategori adi/sevk uyarisi iceriyor (kaynak gerekmeyen icerik), (b) Spesifik iddialar varsa hepsi kaynaklarda var. FALSE sadece sundakilerde don: Yanit "X marketinde Y satiliyor", "Z miktarinda al", "[ozel ilac adi] kullan" gibi SPESIFIK iddialar iceriyor ama kaynaklarda bu spesifik detay YOK. SUPHEDE TRUE don — sadece NET kaynak-disi iddialarda FALSE.

- answer_relevant: Yanit, kullanicinin sordugu SORU ile ayni klinik konuyu mu ele aliyor? Bu kontrol "yanit faydali mi" sorusu DEGIL, "yanit dogru SORUYU mu cevapliyor" sorusudur.

  ASAGIDAKI BASITCE SOR: "Soru X hakkindaysa, yanit X hakkinda mi yoksa tamamen Y hakkinda mi?"

  TRUE don (yanit soruyu ele aliyor):
    • Soru "buzaim ishal oldu", yanit ishal/dehidratasyon hakkinda → TRUE
    • Soru "sut hummasi nedir", yanit hipokalsemi/kalsiyum hakkinda → TRUE
    • Soru muglak ya da tek kelime (orn. "halsiz", "ishal"), yanit muhtemel klinik konuyu ele alip takip sorusu soruyor → TRUE
    • Yanit sorulan konuyla ilgili ama kaynak yetersiz oldugunu belirtip vet'e yonlendiriyor → TRUE (durust yanit)
    • Yanit kismi cevap iceriyor (sorunun bir bolumune cevap) → TRUE
    • Soru kapsam disi ve yanit "bu konu disinda" diyor → TRUE
    • Yanit out-of-scope template'i ("yalnizca buyukbas hayvan...") → TRUE (sistem kararli reddediyor)

  FALSE don (yanit yanlis konuda):
    • Soru "ishal", yanit komple "meme iltihabi/mastit tedavisi" hakkinda → FALSE (klinik konu ortusmuyor)
    • Soru "topallik", yanit komple "solunum hastaligi" hakkinda → FALSE
    • Soru "dogum sonrasi kalkamama", yanit komple "buzagi ishali" hakkinda → FALSE
    • Yanit, soruda gecmeyen ve sorudan cikarilmasi imkansiz bir konu hakkinda → FALSE

  KARAR PRENSIBI: Ayni klinik tablo / sistem / organ icin yanit veriyorsa TRUE.
  Tamamen farkli bir organ/sistem/durum anlatiyorsa FALSE.

  SUPHEDE TRUE don — yanit en azindan KISMEN soruyu ele aliyorsa TRUE. Sadece konu
  TAMAMEN sapma yapmissa FALSE.

ONEMLI: Halusinasyon kontrolu SADECE "grounded" alaninda. Soru-yanit uyumu SADECE "answer_relevant" alaninda. Diger alanlar stil.
SADECE JSON yaz, baska metin EKLEME."""


def _llm_judge_check(
    draft: str,
    docs: list[dict],
    user_role: str,
    user_query: str = "",
) -> str | None:
    """
    LLM-as-judge: 5 boyutta degerlendirme.
      - disclaimer, emergency, sade dil (stil)
      - grounded (yanit kaynaktan mi)
      - answer_relevant (yanit soruyu cevapliyor mu)

    Cerebras gpt-oss-120b @ low reasoning, ~0.5-1 saniye.
    """
    if not draft or len(draft) < 20:
        return None  # cok kisa yanitta judge bos vermeyelim

    # Acil sinyali icin kaynaktaki anahtar kelimelere bak (lokal, LLM'e gitmiyor)
    source_text_full = " ".join(d.get("text", "") for d in docs)
    source_text_lower = source_text_full.lower()
    emergency_keywords = ["fatal", "death", "emergency", "life-threatening"]
    source_has_emergency = any(kw in source_text_lower for kw in emergency_keywords)

    # Grounding check icin kaynak metnini judge'a gonder.
    # 2500 char ~ 600 token, judge'in gormesi icin yeterli; LLM context limiti gevsek tutulur.
    sources_for_judge = source_text_full[:2500] if source_text_full else "(kaynak yok)"

    prompt = JUDGE_PROMPT.format(
        user_role=user_role,
        source_has_emergency="true" if source_has_emergency else "false",
        user_query=(user_query or "(soru alinamadi)")[:500],
        sources=sources_for_judge,
        draft=draft[:2000],
    )

    try:
        llm = ChatOpenAI(
            api_key=settings.cerebras_api_key,
            base_url="https://api.cerebras.ai/v1",
            model="gpt-oss-120b",
            temperature=0,
            # NOT: gpt-oss-120b reasoning modeli. low reasoning ~10-30 token harcar,
            # 4 alanli JSON ~50-100 token. 800 yeterli marj sagliyor.
            # Eski 300 deger bazen reasoning_tokens > content_tokens dengesizliginde
            # content bos donmesine neden oluyordu (bkz. enrich_query ayni bug).
            max_tokens=800,
            reasoning_effort="low",  # type: ignore[call-arg]
        )
        response = llm.invoke(prompt)
        content = str(response.content).strip()

        m = re.search(r"\{[\s\S]*\}", content)
        if not m:
            print(f"[LLM-JUDGE-DEBUG] JSON parse edilemedi. Raw: {content[:200].encode('ascii', 'replace').decode('ascii')}")
            return None

        result = json.loads(m.group())

        # DEBUG (ASCII-safe)
        result_json = json.dumps(result, ensure_ascii=True)
        print(f"[LLM-JUDGE-DEBUG] role={user_role}, emergency={source_has_emergency}, result={result_json}")

        problems: list[str] = []

        if user_role == "producer" and not result.get("disclaimer_present", True):
            problems.append("uretici disclaimer eksik")

        # FIX 1: Sadece producer icin emergency uyarisi zorla. Vet yanitinda
        # 🚨 emoji gerekmez (meslektas zaten baglami biliyor).
        if (
            user_role == "producer"
            and source_has_emergency
            and not result.get("emergency_appropriate", True)
        ):
            problems.append("uretici icin kaynak acil sinyali var ama yanitta uygun acil uyarisi yok")

        if user_role == "producer" and not result.get("lay_language_ok", True):
            problems.append("uretici icin yanit fazla teknik")

        # GROUNDING: yanit kaynaklardaki bilgilere bagli mi?
        # Default True (suphe varsa kabul) — bu sadece NET kaynak-disi iddialarda tetiklenir.
        if not result.get("grounded", True):
            problems.append(
                "yanitta kaynaklarda yer almayan spesifik iddialar var; "
                "sadece kaynaklardaki bilgilerle, gerekirse genel kategori "
                "ifadeleriyle (ornegin spesifik ilac adi yerine 'veterinerin "
                "uygun gordugu tedavi') yeniden yaz"
            )

        # ANSWER RELEVANCE: yanit sorulan soruyu cevapliyor mu?
        # Default True (suphede kabul). Sadece konu tamamen sapmissa FALSE doner.
        if not result.get("answer_relevant", True):
            problems.append(
                "yanit kullanicinin sorusuyla ayni klinik konuda degil; "
                "sorulan konuya odaklan ve kaynaklarda dogrudan ele alinan "
                "bilgiyi kullan, eger kaynaklarda bu konuda yeterli bilgi "
                "yoksa 'bu konuda kaynaklarda yeterli bilgi yok, veterinerinize "
                "danisin' diyerek durust bir yanit ver"
            )

        return "; ".join(problems) if problems else None

    except Exception as e:
        # Judge hatasi critic'i fail etmesin
        print(f"[critic LLM-judge] hata: {e} - skip")
        return None


_SAFE_FALLBACK_PRODUCER = (
    "Bu konuda elimdeki kaynaklarda yeterli ve guvenilir bilgi bulamadim. "
    "Lutfen veteriner hekiminize dogrudan danisin — durumun ciddiyetine gore "
    "muayene gerekebilir.\n\n"
    "⚠️ Bu bilgi karar destegidir. Acil bir durumsa hemen veterinerinize basvurun."
)

_SAFE_FALLBACK_VET = (
    "Elimdeki kaynaklarda bu spesifik konuya iliskin guvenilir bir veri "
    "dogrulanamadi. Halusinasyon riskini onlemek icin yanit uretilmedi; "
    "lutfen baska bir literatur kaynagina danisin."
)


# Retry'da bu mesaj parcalarini iceren judge sonucu -> SAFE FALLBACK
# (stil sorunlari kabul edilir; grounding/relevance fail'i kabul edilmez)
_HALLUCINATION_SIGNATURES = (
    "kaynaklarda yer almayan",   # grounded=false
    "ayni klinik konuda degil",  # answer_relevant=false
)


def critic_node(state: dict) -> dict:
    """
    Critic node — taslak yaniti 5 boyutta dogrular.

    Mantik:
      - attempts=0: tum check'ler, sorun varsa retry
      - attempts=1: judge YINE calisir. Stil sorunlari (disclaimer/lay_lang/emergency)
        kabul edilir; ANCAK grounded=false veya answer_relevant=false ise SAFE FALLBACK
        ("yetersiz kaynak") yaniti yazilir — halusinasyon yayinlanmaz.
    """
    raw_draft = state.get("draft_response", "")
    docs = state.get("retrieved_docs", [])
    user_role = state.get("user_role", "producer")
    attempts = state.get("critic_attempts", 0)

    # Son kullanici mesajini cikar — LLM judge'in answer_relevant kontrolu icin gerekli
    user_query = ""
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, dict) and msg.get("role") == "user":
            user_query = msg.get("content", "")
            break
        elif hasattr(msg, "type") and msg.type == "human":
            user_query = msg.content
            break

    # SANITIZE: kozmetik sorunlari LLM cagirmadan temizle
    draft = _sanitize_draft(raw_draft, user_role)
    state["draft_response"] = draft  # generator retry alirsa temizlenmis halini gormesin diye

    # Fallback yaniti (LLM hatasi, rate limit vs.) ise critic atla
    if state.get("response_status") == "fallback":
        state["final_response"] = draft
        state["response_status"] = "accepted"
        audit_log(state, "critic_skip_fallback", reason="Generator fallback — critic atlanir")
        return state

    # Retry sonrasi: judge'i YINE calistir, ama sadece halusinasyon/relevance icin reddet
    if attempts >= 1:
        judge_result = _llm_judge_check(draft, docs, user_role, user_query=user_query)
        is_hallucination = judge_result and any(sig in judge_result for sig in _HALLUCINATION_SIGNATURES)

        if is_hallucination:
            # Halusinasyon veya topic mismatch retry sonrasi hala var -> SAFE FALLBACK
            fallback = _SAFE_FALLBACK_PRODUCER if user_role == "producer" else _SAFE_FALLBACK_VET
            state["final_response"] = fallback
            state["response_status"] = "rejected_safe_fallback"
            audit_log(
                state,
                "critic_safe_fallback",
                reason=f"Retry sonrasi grounded/relevance fail: {judge_result[:150]}",
            )
        else:
            # Stil sorunlari retry'da kabul (latency koruma)
            state["final_response"] = draft
            state["response_status"] = "accepted_after_max_retries"
            audit_log(state, "critic_max_retries", reason="Stil sorunlari kabul, halusinasyon yok")
        return state

    # HIBRIT CRITIC:
    #  - Hard rules (regex/keyword): sifir maliyet, kesin yakalamalar
    #  - LLM-judge (Cerebras gpt-oss-120b low): paraphrase ve semantik
    # Her check'in adi ile birlikte logla — debug-before-fix metodolojisi
    check_results = {
        "hard:source_citation": _check_source_citation(draft, docs, user_role),
        "hard:numerical_hallucination": _check_hallucination(draft, docs),
        "hard:role_compliance": _check_role_compliance(draft, user_role),
        "llm_judge": _llm_judge_check(draft, docs, user_role, user_query=user_query),
    }

    # ASCII-safe debug print — Windows cp1254 encoding crashine karsi
    triggered = [(name, reason) for name, reason in check_results.items() if reason is not None]
    if triggered:
        print(f"[CRITIC-TRIGGER] attempt={attempts + 1}, triggered_checks={len(triggered)}")
        for name, reason in triggered:
            # Unicode karakter problemlerini onle
            safe_reason = reason.encode("ascii", "replace").decode("ascii")[:200]
            print(f"  - {name}: {safe_reason}")

    rejections = [f"[{name}] {reason}" for name, reason in triggered]

    if rejections:
        state["critic_rejection_reasons"] = rejections
        state["critic_attempts"] = attempts + 1
        state["response_status"] = "rejected"

        audit_log(
            state,
            "critic_rejected",
            reason=rejections,
        )
    else:
        state["final_response"] = draft
        state["critic_rejection_reasons"] = []
        state["response_status"] = "accepted"

        audit_log(state, "critic_accepted")

    return state
