"""
PaytarAI — Clarification Node

Retriever sonrasi rerank top sigmoid skoru `CLARIFY_RERANK_THRESHOLD` (0.50) altinda
ise generator'i atlayip kullaniciya HEDEFLI takip sorulari sorariz. Sorulari ve olasi
ayirici tani listesini Llama-3.3-70B (OpenRouter) tek bir JSON cagrisiyla uretir.

Niye LLM (template degil):
  - "Detay ver" turu sabit metinler robotik, hangi yonde detay istedigimizi
    kullaniciya soylemez.
  - Tibbi soruda chunk'larda gecen konular (asidoz, kursun, mikotoksin vb.)
    cikartilip hedefli sorularla beraber gosterilirse kullanici ne sorduğumuzu
    anlar — "evet ineğim körlük var" gibi gercekten faydali bilgi yazar.

Max clarification turu: CLARIFICATION_MAX_ATTEMPTS (2).
Loop sayisi state['clarification_attempts'] ile takip edilir. Asilirsa
fallback template doner (LLM yok).

Akis:
  rerank_top < 0.50 → clarification_node:
    1) Top-3 chunk basligi + 1 satir snippet'i LLM'e ver
    2) LLM JSON donur: {differentials, follow_up_questions, intro}
    3) Insan-okunabilir metin olarak final_response'a goister
    4) clarification_attempts++ ve response_status = 'clarification_needed'
"""

from __future__ import annotations

import json
import re
import time

from langchain_openai import ChatOpenAI

from app.config import settings
from app.graph.audit import audit_log
from app.graph.debug_trace import trace_node, trim_text


CLARIFICATION_MAX_ATTEMPTS = 2


# ─────────────────────────────────────────────────────────────────
# LLM SINGLETON
# ─────────────────────────────────────────────────────────────────

_clarify_llm: ChatOpenAI | None = None


def _get_clarify_llm() -> ChatOpenAI:
    """OpenRouter Llama-3.3-70B-Instruct, JSON mode."""
    global _clarify_llm
    if _clarify_llm is None:
        _clarify_llm = ChatOpenAI(
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            model="meta-llama/llama-3.3-70b-instruct",
            temperature=0.2,
            max_tokens=600,
            model_kwargs={"response_format": {"type": "json_object"}},
            default_headers={
                "HTTP-Referer": "https://github.com/paytar-ai",
                "X-Title": "PaytarAI",
            },
        )
    return _clarify_llm


# ─────────────────────────────────────────────────────────────────
# PROMPT
# ─────────────────────────────────────────────────────────────────

CLARIFY_PROMPT = """Sen buyukbas veteriner asistanisin. Kullanicinin sorgusu kaynaklarimda zayif esleme
verdi (rerank_top={rerank_top:.2f}). Yani sorgusu ya cok genel, ya da kaynaklarda dogrudan cevabi yok.

KULLANICI SORGUSU (turn {turn}, max {max_turns}):
{query}

KAYNAKLARDA EN ALAKALI GORUNEN CHUNK BASLIKLARI:
{chunks_block}

GOREVIN:
1) Kaynak basliklarindan 3-4 OLASI AYIRICI TANI / KONU cikar. Net hastalik
   adi/durum (rumen asidozu, kursun zehirlenmesi, listeriosis, mikotoksin vb.).
   Kaynakta YOKSA UYDURMA.
2) Kullaniciya soracagimiz 3 SPESIFIK takip sorusu uret. Sorular sorgudaki
   eksik bilgilere yonelik olmali (belirti, yas, sure, baglam, sayi). Genel
   "detay ver" degil, hedefli.
3) Kisa bir "intro" cumlesi yaz (1 cumle, neden detay istedigini sade soyle).

ROL: kullanici "{user_role}". {role_hint}

JSON FORMAT (yalniz bu, markdown YOK):
{{
  "intro": "Tek cumle giris...",
  "differentials": ["Tani 1", "Tani 2", "Tani 3"],
  "follow_up_questions": ["Soru 1?", "Soru 2?", "Soru 3?"]
}}

ONEMLI:
- Sorular Turkce, kisa ve net olmali.
- Differentials Turkce hastalik adi (parantez icinde Ingilizce/Latince konabilir).
- follow_up_questions listesi 2-3 oge ARASI olmali.
- differentials listesi 3-4 oge ARASI olmali.
- Hicbir alan bos olmasin."""


_ROLE_HINTS = {
    "producer": (
        "Ciftciyle konusuyorsun — sade dil, teknik jargon az. "
        "Sorular gunluk gozlemden cikabilecek seyler olsun "
        "(\"dışkı rengi nasıl?\", \"ateşi var mı?\")."
    ),
    "veterinarian": (
        "Veteriner hekim seninle konusuyor — tibbi terim kullanabilirsin. "
        "Sorular klinik bulgu/lab/tani odakli olsun (SCC, dehydrasyon "
        "derecesi, rumen motilitesi vb.)."
    ),
}


# ─────────────────────────────────────────────────────────────────
# YARDIMCILAR
# ─────────────────────────────────────────────────────────────────

def _chunks_block(docs: list[dict]) -> str:
    """Top-3 chunk'i baslik + ilk 200 char snippet seklinde formatla."""
    lines: list[str] = []
    for i, d in enumerate(docs[:3], 1):
        title = (d.get("metadata") or {}).get("source_title", "?")
        text = (d.get("text") or "").strip().replace("\n", " ")
        snippet = text[:200] + ("..." if len(text) > 200 else "")
        score = d.get("rerank_score")
        score_str = f"σ={score:.2f}" if isinstance(score, (int, float)) else ""
        lines.append(f"[Kaynak {i}] {title} {score_str}\n   \"{snippet}\"")
    return "\n".join(lines) if lines else "(kaynak yok)"


def _parse_clarify_json(raw: str) -> dict | None:
    """LLM ciktisi JSON parse + sanity check. Hatali ise None."""
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except Exception:
        return None
    intro = data.get("intro")
    diffs = data.get("differentials")
    questions = data.get("follow_up_questions")
    if not isinstance(intro, str) or not intro.strip():
        return None
    if not isinstance(diffs, list) or not (2 <= len(diffs) <= 5):
        return None
    if not isinstance(questions, list) or not (2 <= len(questions) <= 4):
        return None
    # Stringlere temizle, bos olmamali
    clean_diffs = [str(x).strip() for x in diffs if isinstance(x, str) and x.strip()]
    clean_q = [str(x).strip() for x in questions if isinstance(x, str) and x.strip()]
    if len(clean_diffs) < 2 or len(clean_q) < 2:
        return None
    return {
        "intro": intro.strip(),
        "differentials": clean_diffs[:4],
        "follow_up_questions": clean_q[:3],
    }


def _render_clarification_text(payload: dict, attempt: int) -> str:
    """Insan-okunabilir clarification metnine cevir."""
    parts: list[str] = []
    parts.append(payload["intro"])
    parts.append("")
    parts.append("**Olası nedenler:**")
    for d in payload["differentials"]:
        parts.append(f"- {d}")
    parts.append("")
    parts.append("**Daha doğru cevap için söyler misin:**")
    for i, q in enumerate(payload["follow_up_questions"], 1):
        parts.append(f"{i}. {q}")
    parts.append("")
    parts.append(
        f"_(Takip sorusu {attempt}/{CLARIFICATION_MAX_ATTEMPTS} — "
        "yanıtın doğru cevabı yakalamamıza yardım edecek.)_"
    )
    return "\n".join(parts)


# Max tur asildiginda kullanici-yuzu fallback
def _max_attempts_fallback(user_role: str) -> str:
    if user_role == "producer":
        return (
            "Sorunu netleştirmemize rağmen kaynaklarımda doğrudan eşleşen "
            "bilgi bulamadım. Lütfen veterineriniz hekimine danışın.\n\n"
            "⚠️ Bu bilgi karar destegidir."
        )
    return (
        "Birkaç tur clarification sonrasinda da kaynaklarda yeterli ayirici "
        "tani gerekcesi bulamadim. Guncel veteriner literaturune basvurun."
    )


# ─────────────────────────────────────────────────────────────────
# NODE
# ─────────────────────────────────────────────────────────────────

def clarification_node(state: dict) -> dict:
    """Kullaniciya hedefli takip sorusu sor. LLM ile chunk-grounded."""
    t0 = time.perf_counter()
    docs = state.get("retrieved_docs", []) or []
    rerank_top = float(state.get("rerank_top_score", 0.0))
    user_role = state.get("user_role", "producer")

    # Son kullanici mesajini al
    last_user_msg = ""
    for msg in reversed(state.get("messages", []) or []):
        if isinstance(msg, dict) and msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break
        elif hasattr(msg, "type") and msg.type == "human":
            last_user_msg = msg.content
            break

    attempt = int(state.get("clarification_attempts", 0)) + 1
    state["clarification_attempts"] = attempt

    # ── Max tur asildi → fallback ────────────────────────────
    if attempt > CLARIFICATION_MAX_ATTEMPTS:
        fallback = _max_attempts_fallback(user_role)
        state["final_response"] = fallback
        state["draft_response"] = fallback
        state["response_status"] = "clarification_exhausted"
        state["evidence_confidence"] = "insufficient"
        audit_log(state, "clarify_exhausted",
                  reason=f"attempt={attempt} > max={CLARIFICATION_MAX_ATTEMPTS}")
        trace_node(state, "clarification",
                   input={"reason": "max_attempts", "rerank_top": rerank_top, "attempt": attempt},
                   output={"action": "exhausted_fallback", "draft_out": fallback},
                   latency_ms=(time.perf_counter() - t0) * 1000)
        return state

    # ── Prompt'u kur ─────────────────────────────────────────
    chunks_block = _chunks_block(docs)
    prompt = CLARIFY_PROMPT.format(
        query=last_user_msg or "(soru boş)",
        chunks_block=chunks_block,
        rerank_top=rerank_top,
        turn=attempt,
        max_turns=CLARIFICATION_MAX_ATTEMPTS,
        user_role=user_role,
        role_hint=_ROLE_HINTS.get(user_role, _ROLE_HINTS["producer"]),
    )

    # ── LLM cagrisi ──────────────────────────────────────────
    raw_response = ""
    judge_error = None
    try:
        llm = _get_clarify_llm()
        max_retries = 1
        for attempt_i in range(max_retries + 1):
            try:
                resp = llm.invoke([{"role": "user", "content": prompt}])
                raw_response = str(resp.content).strip()
                break
            except Exception as rate_err:
                msg = str(rate_err)
                if attempt_i >= max_retries:
                    raise
                if "rate_limit" not in msg.lower() and "429" not in msg:
                    raise
                m = re.search(r"try again in ([\d.]+)s", msg)
                wait_s = float(m.group(1)) + 2.0 if m else 10.0
                print(f"[clarify] rate limit, {wait_s:.1f}s bekle")
                time.sleep(wait_s)
    except Exception as e:
        judge_error = str(e)[:300]
        print(f"[clarify] LLM hata: {judge_error}")

    # ── LLM basarisiz → static fallback (LLM yok hata) ──────
    if judge_error or not raw_response:
        fallback_payload = {
            "intro": (
                "Sorunu daha iyi cevaplamak için biraz daha detay gerekiyor."
            ),
            "differentials": [
                d.get("metadata", {}).get("source_title", "?") for d in docs[:3]
            ] or ["(kaynak alınamadı)"],
            "follow_up_questions": [
                "Belirtileri yazar mısın? (ateş, ishal, halsizlik, nöbet, körlük, dışkı durumu)",
                "İnek kaç yaşında ve ne zamandan beri hasta?",
                "Sürüde başka hayvan var mı? Yem/saman koşulları nasıl?",
            ],
        }
        text = _render_clarification_text(fallback_payload, attempt)
        state["final_response"] = text
        state["draft_response"] = text
        state["response_status"] = "clarification_needed"
        state["evidence_confidence"] = "low"
        state["clarification_payload"] = fallback_payload
        audit_log(state, "clarify_static_fallback",
                  reason=judge_error or "empty LLM response")
        trace_node(state, "clarification",
                   input={"prompt": trim_text(prompt, 2000), "attempt": attempt,
                          "rerank_top": rerank_top},
                   output={"action": "static_fallback", "error": judge_error,
                           "raw_response": trim_text(raw_response, 500),
                           "draft_out": text,
                           "payload": fallback_payload},
                   latency_ms=(time.perf_counter() - t0) * 1000)
        return state

    # ── Parse ────────────────────────────────────────────────
    payload = _parse_clarify_json(raw_response)
    if payload is None:
        # Parse hata — static fallback
        fallback_payload = {
            "intro": "Sorununu daha iyi cevaplamak için biraz daha detay gerek.",
            "differentials": ["(kaynak basliklari okunamadi)"],
            "follow_up_questions": [
                "Belirtileri yazar mısın?",
                "Yaş ve süre nedir?",
                "Sürü/ortam durumu nasıl?",
            ],
        }
        text = _render_clarification_text(fallback_payload, attempt)
        state["final_response"] = text
        state["draft_response"] = text
        state["response_status"] = "clarification_needed"
        state["evidence_confidence"] = "low"
        state["clarification_payload"] = fallback_payload
        audit_log(state, "clarify_parse_error", reason="JSON parse failed")
        trace_node(state, "clarification",
                   input={"prompt": trim_text(prompt, 2000), "attempt": attempt,
                          "rerank_top": rerank_top},
                   output={"action": "parse_error_fallback",
                           "raw_response": trim_text(raw_response, 1500),
                           "draft_out": text,
                           "payload": fallback_payload},
                   latency_ms=(time.perf_counter() - t0) * 1000)
        return state

    # ── Basari ───────────────────────────────────────────────
    text = _render_clarification_text(payload, attempt)
    state["final_response"] = text
    state["draft_response"] = text
    state["response_status"] = "clarification_needed"
    state["evidence_confidence"] = "low"
    state["clarification_payload"] = payload
    audit_log(state, "clarify_done",
              reason=f"attempt={attempt}, diffs={len(payload['differentials'])}, "
                     f"qs={len(payload['follow_up_questions'])}, rerank={rerank_top:.2f}")
    trace_node(state, "clarification",
               input={"prompt": trim_text(prompt, 2000), "attempt": attempt,
                      "rerank_top": rerank_top, "n_chunks": len(docs)},
               output={"action": "clarification_needed",
                       "raw_response": trim_text(raw_response, 1500),
                       "draft_out": text,
                       "payload": payload,
                       "model": "meta-llama/llama-3.3-70b-instruct"},
               latency_ms=(time.perf_counter() - t0) * 1000)
    return state
