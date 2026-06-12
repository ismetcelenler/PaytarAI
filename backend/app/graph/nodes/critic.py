"""
PaytarAI — Critic Node (LLM-judge only)

Tek katmanli, scalable kalite kontrolu. Onceki hard-rule katmanlari
(sanitize regex enum'lari + hard rules) sokuldu — endustri standardi medical RAG
sistemleri (OpenEvidence, CRAG, FACTSCORE) yalnizca LLM-judge + skor harmanlamasi
kullaniyor; hand-curated ilac/term listeleri olceklenmiyor.

Akis:
  1) Generator fallback metni geldiyse critic atlanir (statik guvenli metin)
  2) LLM-judge cagrilir (Cerebras gpt-oss-120b, low reasoning, JSON 5 boyut)
  3) Judge sorun bildirirse → critic_rejected → generator retry alir
  4) Judge SILENT FAIL ederse (exception, parse error) → FAIL-CLOSED:
       attempts=0 → reject + retry; attempts>=1 → SAFE FALLBACK
     (Eski davranis "silent fail → accept" idi; bu kritik bypass kapatildi.)
  5) Retry sonrasi (attempts>=1):
       - grounded=false veya answer_relevant=false → SAFE FALLBACK
       - sadece stil sorunlari → kabul (latency koruma)
"""

import json
import re
import time

from langchain_openai import ChatOpenAI

from app.config import settings
from app.graph.audit import audit_log
from app.graph.debug_trace import trace_node, trim_text


# ---------------------------------------------------------------
# LLM-JUDGE prompt
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


# Judge sonucundan hangi failure'lar SAFE FALLBACK tetikler
_HALLUCINATION_SIGNATURES = (
    "kaynaklarda yer almayan",   # grounded=false
    "ayni klinik konuda degil",  # answer_relevant=false
)


# ---------------------------------------------------------------
# SAFE FALLBACK metinleri
# ---------------------------------------------------------------

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


# ---------------------------------------------------------------
# LLM-JUDGE — DONUS: (problems: str | None, judge_succeeded: bool)
# ---------------------------------------------------------------

def _llm_judge_check(
    draft: str,
    docs: list[dict],
    user_role: str,
    user_query: str = "",
) -> tuple[str | None, bool, dict]:
    """
    LLM-as-judge.

    Donen tuple:
      - problems: judge'in tespit ettigi sorunlarin string'i veya None
      - judge_succeeded: judge cagrisinin GERCEKTEN tamamlandigini gosterir
      - debug: {prompt, raw_response, parsed_json, error} — trace icin
    """
    debug: dict = {}

    if not draft or len(draft) < 20:
        debug["skipped"] = "draft too short"
        return None, True, debug

    source_text_full = " ".join(d.get("text", "") for d in docs)
    source_text_lower = source_text_full.lower()
    emergency_keywords = ["fatal", "death", "emergency", "life-threatening"]
    source_has_emergency = any(kw in source_text_lower for kw in emergency_keywords)

    sources_for_judge = source_text_full[:2500] if source_text_full else "(kaynak yok)"

    prompt = JUDGE_PROMPT.format(
        user_role=user_role,
        source_has_emergency="true" if source_has_emergency else "false",
        user_query=(user_query or "(soru alinamadi)")[:500],
        sources=sources_for_judge,
        draft=draft[:2000],
    )
    debug["prompt"] = prompt
    debug["source_has_emergency"] = source_has_emergency

    try:
        llm = ChatOpenAI(
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            model="openai/gpt-oss-120b",
            temperature=0,
            max_tokens=800,
            reasoning_effort="low",  # type: ignore[call-arg]
            default_headers={
                "HTTP-Referer": "https://github.com/paytar-ai",
                "X-Title": "PaytarAI",
            },
        )
        response = llm.invoke(prompt)
        content = str(response.content).strip()
        debug["raw_response"] = content

        m = re.search(r"\{[\s\S]*\}", content)
        if not m:
            print(
                f"[LLM-JUDGE-DEBUG] JSON parse edilemedi (FAIL-CLOSED). "
                f"Raw: {content[:200].encode('ascii', 'replace').decode('ascii')}"
            )
            debug["parse_error"] = True
            return None, False, debug

        result = json.loads(m.group())
        debug["parsed_json"] = result
        print(
            f"[LLM-JUDGE-DEBUG] role={user_role}, emergency={source_has_emergency}, "
            f"result={json.dumps(result, ensure_ascii=True)}"
        )

        problems: list[str] = []

        if user_role == "producer" and not result.get("disclaimer_present", True):
            problems.append("uretici disclaimer eksik")

        if (
            user_role == "producer"
            and source_has_emergency
            and not result.get("emergency_appropriate", True)
        ):
            problems.append("uretici icin kaynak acil sinyali var ama yanitta uygun acil uyarisi yok")

        if user_role == "producer" and not result.get("lay_language_ok", True):
            problems.append("uretici icin yanit fazla teknik")

        if not result.get("grounded", True):
            problems.append(
                "yanitta kaynaklarda yer almayan spesifik iddialar var; "
                "sadece kaynaklardaki bilgilerle, gerekirse genel kategori "
                "ifadeleriyle yeniden yaz"
            )

        if not result.get("answer_relevant", True):
            problems.append(
                "yanit kullanicinin sorusuyla ayni klinik konuda degil; "
                "sorulan konuya odaklan ve kaynaklarda dogrudan ele alinan "
                "bilgiyi kullan"
            )

        debug["problems"] = problems
        return ("; ".join(problems) if problems else None), True, debug

    except Exception as e:
        print(f"[critic LLM-judge] HATA (FAIL-CLOSED): {e}")
        debug["error"] = str(e)[:300]
        return None, False, debug


# ---------------------------------------------------------------
# CRITIC NODE
# ---------------------------------------------------------------

def critic_node(state: dict) -> dict:
    """
    Critic — tek katmanli, LLM-judge tabanli kalite kontrolu.
    """
    t0 = time.perf_counter()
    draft = state.get("draft_response", "")
    docs = state.get("retrieved_docs", [])
    user_role = state.get("user_role", "producer")
    attempts = state.get("critic_attempts", 0)

    user_query = ""
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, dict) and msg.get("role") == "user":
            user_query = msg.get("content", "")
            break
        elif hasattr(msg, "type") and msg.type == "human":
            user_query = msg.content
            break

    # Generator fallback yaniti (LLM hata/rate limit vs.) → critic atla
    if state.get("response_status") == "fallback":
        state["final_response"] = draft
        state["response_status"] = "accepted"
        audit_log(state, "critic_skip_fallback", reason="Generator fallback metni (statik)")
        trace_node(state, "critic",
                   input={"draft": trim_text(draft), "attempts": attempts},
                   output={"decision": "skip_fallback"},
                   latency_ms=(time.perf_counter() - t0) * 1000)
        return state

    judge_problems, judge_ok, judge_debug = _llm_judge_check(draft, docs, user_role, user_query=user_query)
    is_hallucination_sig = (
        judge_problems is not None
        and any(sig in judge_problems for sig in _HALLUCINATION_SIGNATURES)
    )

    # ── FAIL-CLOSED: judge cagrisi basarisiz olduysa ────────────
    if not judge_ok:
        if attempts >= 1:
            # Retry de basarisiz → SAFE FALLBACK
            fallback = _SAFE_FALLBACK_PRODUCER if user_role == "producer" else _SAFE_FALLBACK_VET
            state["final_response"] = fallback
            state["response_status"] = "rejected_safe_fallback"
            audit_log(
                state,
                "critic_safe_fallback",
                reason="LLM-judge silent fail x2 — halusinasyon riski varsayildi",
            )
        else:
            state["critic_rejection_reasons"] = [
                "[llm_judge] judge cagrisi yapilamadi (Cerebras hata/parse fail) — fail-closed retry"
            ]
            state["critic_attempts"] = attempts + 1
            state["response_status"] = "rejected"
            audit_log(
                state,
                "critic_rejected",
                reason="LLM-judge silent fail — fail-closed retry tetiklendi",
            )
        _emit_trace(state, t0, draft, attempts, user_role, user_query,
                    judge_problems, judge_ok, judge_debug,
                    decision=state["response_status"])
        return state

    # ── RETRY YOLU ──────────────────────────────────────────────
    if attempts >= 1:
        if is_hallucination_sig:
            fallback = _SAFE_FALLBACK_PRODUCER if user_role == "producer" else _SAFE_FALLBACK_VET
            state["final_response"] = fallback
            state["response_status"] = "rejected_safe_fallback"
            audit_log(
                state,
                "critic_safe_fallback",
                reason=f"Retry sonrasi grounded/relevance fail: {judge_problems[:150] if judge_problems else ''}",
            )
        else:
            state["final_response"] = draft
            state["response_status"] = "accepted_after_max_retries"
            audit_log(
                state,
                "critic_max_retries",
                reason=f"Stil sorunlari kabul: {(judge_problems or '(yok)')[:150]}",
            )
        _emit_trace(state, t0, draft, attempts, user_role, user_query,
                    judge_problems, judge_ok, judge_debug,
                    decision=state["response_status"])
        return state

    # ── ILK GECIS ───────────────────────────────────────────────
    if judge_problems:
        print(f"[CRITIC-TRIGGER] attempt={attempts + 1}, judge_problems={judge_problems[:200].encode('ascii', 'replace').decode('ascii')}")
        state["critic_rejection_reasons"] = [f"[llm_judge] {judge_problems}"]
        state["critic_attempts"] = attempts + 1
        state["response_status"] = "rejected"
        audit_log(state, "critic_rejected", reason=judge_problems[:200])
    else:
        state["final_response"] = draft
        state["critic_rejection_reasons"] = []
        state["response_status"] = "accepted"
        audit_log(state, "critic_accepted")

    _emit_trace(state, t0, draft, attempts, user_role, user_query,
                judge_problems, judge_ok, judge_debug,
                decision=state["response_status"])
    return state


def _emit_trace(state, t0, draft, attempts, user_role, user_query,
                judge_problems, judge_ok, judge_debug, decision):
    """Critic node icin debug trace ekle."""
    trace_node(
        state, "critic",
        input={
            "draft": trim_text(draft, 2000),
            "user_query": user_query,
            "user_role": user_role,
            "attempts_in": attempts,
            "docs_count": len(state.get("retrieved_docs", [])),
        },
        output={
            "decision": decision,
            "judge_ok": judge_ok,
            "judge_problems": judge_problems,
            "judge_prompt": trim_text(judge_debug.get("prompt", ""), 2500),
            "judge_raw_response": trim_text(judge_debug.get("raw_response", ""), 1200),
            "judge_parsed_json": judge_debug.get("parsed_json"),
            "judge_error": judge_debug.get("error"),
            "judge_parse_error": judge_debug.get("parse_error"),
            "judge_skipped": judge_debug.get("skipped"),
            "source_has_emergency": judge_debug.get("source_has_emergency"),
        },
        latency_ms=(time.perf_counter() - t0) * 1000,
    )
