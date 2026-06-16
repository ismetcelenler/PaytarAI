"""
PaytarAI — Sentence-Level Grounding Filter (Turk-LettuceDetect powered)

v3 mimari: LLM-judge (Llama-3.3-70B / 35-128s) yerine yerel
EuroBERT-tr (210M / ~500ms) token-level hallucination classifier.

Model: newmindai/lettucedect-210m-eurobert-tr-v1
  - RAGTruth-TR uzerinde fine-tune
  - Input: [context, question, answer]
  - Output: token-level supported(0) / hallucinated(1) labels + character span'lar
  - Multilingual (EuroBERT base) -> hem Turkce hem Ingilizce icerigi yargilar
  - F1: 0.7777 overall, QA 0.7317, data-to-text 0.8030
  - MIT license

Eski LLM-based grounding'in dezavantajlari (kaldirildi):
  - 35-128s latency (Llama-3.3 70B OpenRouter)
  - Atomic claim decomposition prompt'u JSON'un siramasini istiyordu, kirilgan
  - "Supheli supported=true" bias modele yerlesti, multi-claim cumleleri kaciriyordu

Yeni mimarinin avantajlari:
  - ~500ms inference (RTX 3060)
  - Token-level — multi-claim cumlede 5 iddiadan sadece 1'i destekleniyorsa
    geri kalan 4'unu char span olarak isaretler
  - Sentence-level decision: spanlarin cumledeki toplam orani > 30% ise drop
  - Hicbir LLM cagrisi yok — rate-limit veya 429 sorunlari ortadan kalkar
"""

from __future__ import annotations

import re
import time

from app.graph.audit import audit_log
from app.graph.debug_trace import trace_node, trim_text

# ─────────────────────────────────────────────────────────────────
# MODEL SINGLETON — lazy load, worker process'te bir kere yukleniyor
# ─────────────────────────────────────────────────────────────────

_detector = None  # HallucinationDetector instance
_detector_load_failed = False


def _get_detector():
    """Lazy-load Turk-LettuceDetect EuroBERT-tr model.

    Returns:
        HallucinationDetector instance or None if load failed.
    """
    global _detector, _detector_load_failed
    if _detector is not None:
        return _detector
    if _detector_load_failed:
        return None

    try:
        from lettucedetect.models.inference import HallucinationDetector  # type: ignore
        t0 = time.perf_counter()
        _detector = HallucinationDetector(
            method="transformer",
            model_path="newmindai/lettucedect-210m-eurobert-tr-v1",
            device="cuda",
        )
        print(f"[lettucedetect] Model yuklendi: {time.perf_counter() - t0:.1f}s")
        return _detector
    except Exception as e:
        _detector_load_failed = True
        print(f"[lettucedetect] YUKLENEMEDI: {e}")
        return None


# ─────────────────────────────────────────────────────────────────
# CUMLE BOLME (sentence segmentation)
# ─────────────────────────────────────────────────────────────────

_SENT_SPLIT_RE = re.compile(
    r"(?<=[.!?])\s+(?=[A-ZĞÜŞİÖÇ\*\-0-9])|\n+"
)


def _split_sentences(text: str) -> list[tuple[int, int, str]]:
    """Yaniti cumlelere bol, her cumle icin (start_char, end_char, text) don.

    Char index'leri orijinal yanitta nereye denk geldigi bilgisini korur —
    LettuceDetect span'larini cumlelere map'lemek icin gerekli.
    """
    out: list[tuple[int, int, str]] = []
    pos = 0
    for line in re.split(r"(\n+)", text):
        if not line.strip():
            pos += len(line)
            continue
        # Bullet/numbered list satirini tek cumle say
        if re.match(r"^\s*(\*\*|[-*]|\d+\.)", line):
            out.append((pos, pos + len(line), line.strip()))
            pos += len(line)
            continue
        # Normal satir — noktalama uzerinden boL
        sub_pos = pos
        for piece in re.split(r"(?<=[.!?])\s+", line):
            piece = piece.rstrip()
            if piece:
                start = text.find(piece, sub_pos)
                if start == -1:
                    start = sub_pos
                end = start + len(piece)
                out.append((start, end, piece))
                sub_pos = end
        pos += len(line)
    return out


# ─────────────────────────────────────────────────────────────────
# SENTENCE-LEVEL DECISION
# ─────────────────────────────────────────────────────────────────

# Bir cumledeki hallucination char'larinin orani bu degeri asarsa cumle drop.
SENTENCE_HALLUC_THRESHOLD = 0.30

# Tum yanitin char'larinin %X'i hallucination ise safe_fallback'e dustur.
# Specific/generic ayrimi yapmadan global oran — generic cumleler de sayilir.
ANSWER_HALLUC_THRESHOLD = 0.40

# Noise filter — LettuceDetect bazen Turkce ek/alt-token'lari yanlislikla
# halusinasyon olarak isaretliyor ("ım", "kl", '"', "u" gibi). Bu degerler
# altindaki span'lar atilir.
MIN_SPAN_CHARS = 4
MIN_SPAN_CONFIDENCE = 0.60


def _filter_noise_spans(spans: list[dict]) -> list[dict]:
    """LettuceDetect sub-token gurultusunu sil:
      - 4 karakterden kisa metin (TR ekleri, parantezler vs)
      - %60 alti confidence (model tereddutlu)
      - Sadece noktalama/bosluk olan span'lar
    """
    out = []
    for sp in spans:
        text = (sp.get("text") or "").strip()
        if len(text) < MIN_SPAN_CHARS:
            continue
        if float(sp.get("confidence", 0.0)) < MIN_SPAN_CONFIDENCE:
            continue
        if re.fullmatch(r"[\W_]+", text):
            continue
        out.append(sp)
    return out


def _annotate_sentences(
    answer: str,
    spans: list[dict],
) -> list[dict]:
    """Her cumle icin: text, hallucination_ratio, kept ve span listesi don.

    Args:
        answer: Generator'in raw yaniti.
        spans: LettuceDetect cikti [{"start": int, "end": int, "text": str, "confidence": float}, ...]

    Returns:
        Cumle bazli annotated list.
    """
    sentences = _split_sentences(answer)
    out: list[dict] = []

    for s_start, s_end, s_text in sentences:
        s_len = max(s_end - s_start, 1)

        # Bu cumlenin char araliginin spans ile kesisimini hesapla
        halluc_chars = 0
        sent_spans: list[dict] = []
        for sp in spans:
            sp_s, sp_e = int(sp.get("start", 0)), int(sp.get("end", 0))
            overlap_start = max(s_start, sp_s)
            overlap_end = min(s_end, sp_e)
            if overlap_end > overlap_start:
                halluc_chars += overlap_end - overlap_start
                sent_spans.append({
                    "text": sp.get("text", ""),
                    "confidence": float(sp.get("confidence", 0.0)),
                    "relative_start": max(0, sp_s - s_start),
                    "relative_end": min(s_len, sp_e - s_start),
                })

        ratio = halluc_chars / s_len
        supported = ratio < SENTENCE_HALLUC_THRESHOLD

        out.append({
            "text": s_text,
            # Frontend ile uyumluluk icin: tum cumleler "specific" (artik LLM siniflandirmiyoruz)
            "type": "specific" if sent_spans else "generic",
            "chunk": None,  # LettuceDetect chunk-attribution yapmiyor, sadece overall
            "supported": supported,
            "hallucination_ratio": round(ratio, 3),
            "hallucination_spans": sent_spans,
            # Atomic_claims frontend backward-compat icin — bos liste
            "atomic_claims": [],
        })

    return out


# ─────────────────────────────────────────────────────────────────
# REASSEMBLE
# ─────────────────────────────────────────────────────────────────

def _reassemble(kept_sentences: list[dict]) -> str:
    """Tutulan cumleleri orijinal sira ile birlestir."""
    if not kept_sentences:
        return ""

    lines: list[str] = []
    for s in kept_sentences:
        text = s["text"].rstrip()
        if re.match(r"^\s*(\*\*|[-*]|\d+\.)", text):
            lines.append(text)
        else:
            if lines and not re.match(r"^\s*(\*\*|[-*]|\d+\.)", lines[-1]):
                lines[-1] = lines[-1] + " " + text
            else:
                lines.append(text)
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────
# NODE
# ─────────────────────────────────────────────────────────────────

_SAFE_FALLBACK_PRODUCER = (
    "Bu konuda elimdeki kaynaklarda yeterli bilgi bulamadim. "
    "Lutfen veterineriniz hekimine danisin.\n\n"
    "⚠️ Bu bilgi karar destegidir."
)

_SAFE_FALLBACK_VET = (
    "Elimdeki kaynaklarda bu konuda spesifik bir bilgi dogrulanamadi. "
    "Lutfen guncel veteriner literaturune basvurun."
)


def sentence_grounding_node(state: dict) -> dict:
    """Cumle-seviyesi grounding (Turk-LettuceDetect EuroBERT-tr 210M)."""
    t0 = time.perf_counter()
    draft = state.get("draft_response", "")
    docs = state.get("retrieved_docs", [])
    user_role = state.get("user_role", "producer")

    # Generator fallback metni veya cok kisa yanit → grounding atla
    if state.get("response_status") == "fallback":
        audit_log(state, "grounding_skip", reason="Generator fallback metni")
        trace_node(state, "sentence_grounding",
                   input={"reason": "skip", "draft": trim_text(draft, 200)},
                   output={"skipped": True, "reason": "Generator fallback metni"})
        return state

    if not draft or len(draft) < 60:
        audit_log(state, "grounding_skip", reason="Yanit cok kisa")
        trace_node(state, "sentence_grounding",
                   input={"reason": "skip", "draft": draft},
                   output={"skipped": True, "reason": "Yanit cok kisa"})
        return state

    if not docs:
        audit_log(state, "grounding_skip", reason="Kaynak yok")
        trace_node(state, "sentence_grounding",
                   input={"reason": "skip"},
                   output={"skipped": True, "reason": "Kaynak yok"})
        return state

    # Soruyu state'ten cek
    user_query = ""
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, dict) and msg.get("role") == "user":
            user_query = msg.get("content", "")
            break
        elif hasattr(msg, "type") and msg.type == "human":
            user_query = msg.content
            break

    # Top-3 chunk'i tek bir context block'unda birlestir
    context_block = "\n\n".join(
        f"=== Kaynak {i+1} ===\n{d.get('text', '').strip()[:1500]}"
        for i, d in enumerate(docs[:3])
    )

    detector = _get_detector()
    if detector is None:
        audit_log(state, "grounding_skip", reason="LettuceDetect model yuklenemedi")
        trace_node(state, "sentence_grounding",
                   input={"draft_in": trim_text(draft),
                          "context": trim_text(context_block, 1500)},
                   output={"error": "model load failed", "skipped": True})
        return state

    # ─────────────────────────────────────────────────────────
    # TEK LettuceDetect cagrisi — token-level span'lar
    # ─────────────────────────────────────────────────────────
    try:
        t_inf = time.perf_counter()
        raw_spans = detector.predict(
            context=[context_block],
            question=user_query or "Soru bilinmiyor",
            answer=draft,
            output_format="spans",
        ) or []
        inf_ms = (time.perf_counter() - t_inf) * 1000
        # Noise filter: sub-token gurultusunu temizle
        spans = _filter_noise_spans(raw_spans)
        print(
            f"[lettucedetect] inference: {inf_ms:.0f}ms, "
            f"raw spans: {len(raw_spans)}, after noise filter: {len(spans)}"
        )
    except Exception as e:
        err_msg = str(e)
        print(f"[lettucedetect] hata: {err_msg[:200]} — atlaniyor")
        audit_log(state, "grounding_skip", reason=f"LettuceDetect error: {err_msg[:80]}")
        trace_node(state, "sentence_grounding",
                   input={"draft_in": trim_text(draft),
                          "context": trim_text(context_block, 1500)},
                   output={"error": err_msg[:300], "skipped": True})
        return state

    # ─────────────────────────────────────────────────────────
    # Cumle bazli annotation + drop decision
    # ─────────────────────────────────────────────────────────
    sentences = _annotate_sentences(draft, spans)
    total = len(sentences)

    if total == 0:
        audit_log(state, "grounding_skip", reason="0 cumle parse edildi")
        trace_node(state, "sentence_grounding",
                   input={"draft_in": trim_text(draft)},
                   output={"sentences": [], "skipped": True})
        return state

    specific = [s for s in sentences if s["type"] == "specific"]
    generic = [s for s in sentences if s["type"] == "generic"]
    supported_list = [s for s in sentences if s["supported"]]
    unsupported_specific = [s for s in specific if not s["supported"]]

    drop_ratio = len(unsupported_specific) / max(len(specific), 1)
    total_halluc_chars = sum(
        sum(sp["relative_end"] - sp["relative_start"] for sp in s["hallucination_spans"])
        for s in sentences
    )
    total_answer_chars = len(draft)
    answer_halluc_ratio = total_halluc_chars / max(total_answer_chars, 1)

    debug_summary = (
        f"total={total}, with_spans={len(specific)}, clean={len(generic)}, "
        f"dropped={len(unsupported_specific)}, drop_ratio={drop_ratio:.2f}, "
        f"answer_halluc_chars={total_halluc_chars}/{total_answer_chars} ({answer_halluc_ratio:.2%})"
    )
    print(f"[GROUNDING] {debug_summary}")

    if unsupported_specific:
        print(f"[GROUNDING] DROPPED sentences ({len(unsupported_specific)}):")
        for s in unsupported_specific[:5]:
            safe = s["text"][:120].encode("ascii", "replace").decode("ascii")
            print(f"  - ratio={s['hallucination_ratio']:.2f}: {safe}")
            for sp in s["hallucination_spans"][:2]:
                sp_safe = sp["text"][:80].encode("ascii", "replace").decode("ascii")
                print(f"      [X] {sp['confidence']:.2f}: {sp_safe}")

    stats = {
        "total": total,
        "specific": len(specific),
        "generic": len(generic),
        "supported": len(supported_list),
        "dropped": len(unsupported_specific),
        "drop_ratio": round(drop_ratio, 3),
        "answer_halluc_chars": total_halluc_chars,
        "answer_total_chars": total_answer_chars,
        "answer_halluc_ratio": round(answer_halluc_ratio, 3),
        "raw_span_count": len(spans),
        "inference_ms": round(inf_ms, 1),
    }

    latency_ms = (time.perf_counter() - t0) * 1000

    # ─────────────────────────────────────────────────────────
    # Yanit cogu uydurma ise → SAFE FALLBACK
    # Karar metric: ANSWER_HALLUC_RATIO (specific/generic ayrimi olmadan global oran)
    # ─────────────────────────────────────────────────────────
    if answer_halluc_ratio > ANSWER_HALLUC_THRESHOLD:
        fallback = _SAFE_FALLBACK_PRODUCER if user_role == "producer" else _SAFE_FALLBACK_VET
        state["draft_response"] = fallback
        state["grounding_action"] = "safe_fallback"
        audit_log(state, "grounding_safe_fallback",
                  reason=f"answer_halluc_ratio={answer_halluc_ratio:.2f} > {ANSWER_HALLUC_THRESHOLD}: {debug_summary}")
        trace_node(state, "sentence_grounding",
                   input={"draft_in": trim_text(draft),
                          "context": trim_text(context_block, 1500),
                          "chunk_count": len(docs)},
                   output={"sentences": sentences, "stats": stats,
                           "raw_spans": spans[:30],
                           "action": "safe_fallback", "draft_out": fallback,
                           "verifier": "newmindai/lettucedect-210m-eurobert-tr-v1"},
                   latency_ms=latency_ms)
        return state

    # ─────────────────────────────────────────────────────────
    # Desteklenenleri tut, desteklenmeyenleri sil
    # ─────────────────────────────────────────────────────────
    kept = [s for s in sentences if s["supported"]]
    cleaned = _reassemble(kept)

    if not cleaned.strip():
        fallback = _SAFE_FALLBACK_PRODUCER if user_role == "producer" else _SAFE_FALLBACK_VET
        state["draft_response"] = fallback
        state["grounding_action"] = "safe_fallback_empty"
        audit_log(state, "grounding_safe_fallback", reason=f"empty after filter: {debug_summary}")
        trace_node(state, "sentence_grounding",
                   input={"draft_in": trim_text(draft),
                          "context": trim_text(context_block, 1500),
                          "chunk_count": len(docs)},
                   output={"sentences": sentences, "stats": stats,
                           "raw_spans": spans[:30],
                           "action": "safe_fallback_empty", "draft_out": fallback,
                           "verifier": "newmindai/lettucedect-210m-eurobert-tr-v1"},
                   latency_ms=latency_ms)
        return state

    state["draft_response"] = cleaned
    state["grounding_action"] = "filtered" if unsupported_specific else "passed"
    audit_log(state, "grounding_done",
              reason=f"action={state['grounding_action']}, {debug_summary}")
    trace_node(state, "sentence_grounding",
               input={"draft_in": trim_text(draft),
                      "context": trim_text(context_block, 1500),
                      "chunk_count": len(docs)},
               output={"sentences": sentences, "stats": stats,
                       "raw_spans": spans[:30],
                       "action": state["grounding_action"], "draft_out": cleaned,
                       "verifier": "newmindai/lettucedect-210m-eurobert-tr-v1"},
               latency_ms=latency_ms)
    return state
