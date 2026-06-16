"""
PaytarAI — Mini Eval

Her soru icin:
  1) Pipeline'i calistir (POST /chat?debug=true)
  2) Generator'a giden chunk'lari + sentence_grounding'in droppladigi cumleleri cek
  3) LLM-judge ile iki kontrol yap:
     a) Her droplanan cumle: kaynak chunklarda destekleniyor mu? (false positive yakala)
     b) Nihai yanit kullanicinin sorusunu kaynaklardan duzgun cevapliyor mu? (1-5 skor)
  4) Markdown rapor olarak research/mini_eval_<timestamp>.md'ye yaz

Judge LLM: OpenRouter llama-3.3-70b-instruct (hizli, tutarli).
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib import request, error

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

API_BASE = os.environ.get("PAYTAR_API", "http://localhost:8000")
RESEARCH_DIR = Path(__file__).parent.parent / "research"
RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

QUESTIONS = [
    {
        "id": "bloat",
        "user_role": "veterinarian",
        "message": "Sığırlarda karın şişkinliği nedenleri nelerdir?",
    },
    {
        "id": "calf_diarrhea",
        "user_role": "veterinarian",
        "message": "Yenidoğan buzağılarda ishal yapan başlıca etkenler ve ayırıcı tanı nasıldır?",
    },
    {
        "id": "postpartum",
        "user_role": "producer",
        "message": "İneğim doğurduktan 5 gün sonra halsiz yürüyor ve sütü azaldı, ne yapayım?",
    },
    {
        "id": "milk_fever",
        "user_role": "veterinarian",
        "message": "Süt humması (parturient paresis) patogenezi ve tedavisi nedir?",
    },
    {
        "id": "abomasal_displacement",
        "user_role": "veterinarian",
        "message": "Şirden sola kayması (sol abomasal displasman) nasıl teşhis ve tedavi edilir?",
    },
]


# ─────────────────────────────────────────────────────────────────
# JUDGE LLM
# ─────────────────────────────────────────────────────────────────

def _get_judge_llm():
    """Lazy-load OpenRouter llama-3.3-70b judge."""
    from langchain_openai import ChatOpenAI
    from app.config import settings
    return ChatOpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
        model="meta-llama/llama-3.3-70b-instruct",
        temperature=0,
        max_tokens=400,
        default_headers={
            "HTTP-Referer": "https://github.com/paytar-ai",
            "X-Title": "PaytarAI-Eval",
        },
    )


DROP_JUDGE_PROMPT = """Sen bir veteriner literaturu hakemi sin.

KAYNAK METINLER:
{chunks}

ASAGIDAKI CUMLE LettuceDetect tarafindan "kaynaklarda yok, halusinasyon" diye DROP edildi.
Cumlenin gercekten halusinasyon olup olmadigini sen kontrol et:

CUMLE: "{sentence}"

Kaynak metinlerin TAMAMINI dikkatlice oku. Cumledeki iddialar (organ adlari,
prosedurler, sayisal degerler, hastalik adlari) kaynaklarda DOGRUDAN veya
YAKIN PARAFRAZ olarak geciyor mu?

Cikti format (sadece bu iki satir):
SUPPORTED: EVET / KISMI / HAYIR
GEREKCE: [10-30 kelime, somut kaynak referansiyla]
"""

ANSWER_JUDGE_PROMPT = """Sen bir veteriner literaturu hakemi sin.

KULLANICI SORUSU: {question}

KAYNAK METINLER:
{chunks}

YANIT:
{answer}

Yanit, kullanicinin sorusunu KAYNAK METINLERE DAYANARAK duzgun cevapliyor mu?

Puan kriterleri:
- 5: Sorunun tum kismini kaynaklardan duzgun, dogru, eksiksiz cevapliyor
- 4: Iyi cevap, ama 1-2 onemsiz eksik veya hafif sapma var
- 3: Vasat — kismi cevap, bazi kismi kaynaklardan, bazi yerlerde belirsiz
- 2: Zayif — yanit sorunun ana kismini kacirmis veya bazi kaynak-disi seyler var
- 1: Yetersiz — sorunun ozune deginmemis, yanlis veya bos

Cikti format (sadece bu iki satir):
PUAN: [1-5]
GEREKCE: [30-60 kelime, neden bu puani verdigini somut yaz]
"""


def _judge_drop(judge, chunks_text: str, sentence: str) -> dict:
    prompt = DROP_JUDGE_PROMPT.format(chunks=chunks_text, sentence=sentence)
    try:
        response = judge.invoke(prompt)
        text = str(response.content).strip()
        m_sup = re.search(r"SUPPORTED:\s*(EVET|KISMI|HAYIR)", text, re.IGNORECASE)
        m_rea = re.search(r"GEREKCE:\s*(.+)", text, re.IGNORECASE | re.DOTALL)
        return {
            "supported": m_sup.group(1).upper() if m_sup else "?",
            "reason": (m_rea.group(1).strip() if m_rea else text)[:250],
            "raw": text[:500],
        }
    except Exception as e:
        return {"supported": "ERROR", "reason": str(e)[:200], "raw": ""}


def _judge_answer(judge, question: str, chunks_text: str, answer: str) -> dict:
    prompt = ANSWER_JUDGE_PROMPT.format(question=question, chunks=chunks_text, answer=answer)
    try:
        response = judge.invoke(prompt)
        text = str(response.content).strip()
        m_score = re.search(r"PUAN:\s*([1-5])", text)
        m_rea = re.search(r"GEREKCE:\s*(.+)", text, re.IGNORECASE | re.DOTALL)
        return {
            "score": int(m_score.group(1)) if m_score else 0,
            "reason": (m_rea.group(1).strip() if m_rea else text)[:400],
            "raw": text[:600],
        }
    except Exception as e:
        return {"score": 0, "reason": str(e)[:200], "raw": ""}


# ─────────────────────────────────────────────────────────────────
# PIPELINE CAGRISI
# ─────────────────────────────────────────────────────────────────

def call_api(q: dict) -> dict:
    body = json.dumps({
        "message": q["message"],
        "user_role": q["user_role"],
        "input_source": "text",
        "debug": True,
        "thread_id": f"eval-{q['id']}",
    }).encode("utf-8")
    req = request.Request(
        f"{API_BASE}/api/v1/chat",
        data=body, method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())


def extract_eval_data(api_resp: dict) -> dict:
    """Trace'den eval icin gerekli alanlari cikar."""
    trace = api_resp.get("debug_trace", [])
    chunks: list[dict] = []
    draft_in = ""
    sentences: list[dict] = []
    draft_out = ""

    for e in trace:
        if e.get("node") == "retriever":
            chunks = e.get("output", {}).get("reranked_top_k", []) or []
        elif e.get("node") == "sentence_grounding":
            draft_in = e.get("input", {}).get("draft_in", "")
            out = e.get("output", {}) or {}
            sentences = out.get("sentences", []) or []
            draft_out = out.get("draft_out", "")

    dropped = [s for s in sentences if not s.get("supported", True)]

    chunks_text = "\n\n".join(
        f"=== Kaynak {i+1} ({c.get('language','?')}) — {c.get('title','?')} ===\n{c.get('text_full','')}"
        for i, c in enumerate(chunks)
    )

    return {
        "final_response": api_resp.get("response", ""),
        "chunks": chunks,
        "chunks_text": chunks_text,
        "draft_in": draft_in,
        "draft_out": draft_out,
        "all_sentences": sentences,
        "dropped_sentences": dropped,
    }


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────

def main() -> int:
    print(f"\n{'='*90}")
    print(f"  PaytarAI Mini Eval — {len(QUESTIONS)} soru")
    print(f"{'='*90}\n")

    judge = _get_judge_llm()

    results = []
    for i, q in enumerate(QUESTIONS, 1):
        print(f"\n[{i}/{len(QUESTIONS)}] {q['id']} ({q['user_role']})")
        print(f"  Soru: {q['message'][:90]}")

        t0 = time.time()
        try:
            api_resp = call_api(q)
        except Exception as e:
            print(f"  ✗ API hata: {e}")
            results.append({"q": q, "error": str(e)})
            continue
        api_time = time.time() - t0

        data = extract_eval_data(api_resp)
        n_chunks = len(data["chunks"])
        n_dropped = len(data["dropped_sentences"])
        print(f"  ✓ Pipeline {api_time:.1f}s · {n_chunks} chunk · {n_dropped} cumle drop")

        # Drop kontrolu
        drop_judgments = []
        for j, s in enumerate(data["dropped_sentences"], 1):
            sent = s["text"]
            print(f"    [drop {j}/{n_dropped}] {sent[:70]}...")
            j_drop = _judge_drop(judge, data["chunks_text"][:6000], sent)
            drop_judgments.append({"sentence": sent, **j_drop})
            print(f"      -> {j_drop['supported']}: {j_drop['reason'][:80]}")

        # Cevap kalitesi
        print(f"    [cevap kalitesi yargilaniyor...]")
        ans_j = _judge_answer(judge, q["message"], data["chunks_text"][:6000], data["final_response"])
        print(f"      PUAN: {ans_j['score']} | {ans_j['reason'][:100]}")

        results.append({
            "q": q,
            "api_time_s": round(api_time, 1),
            "data": data,
            "drop_judgments": drop_judgments,
            "answer_judgment": ans_j,
        })

    # Rapor
    return write_report(results)


def write_report(results: list[dict]) -> int:
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    path = RESEARCH_DIR / f"mini_eval_{ts}.md"

    # Aggregate
    total_drops = sum(len(r.get("drop_judgments") or []) for r in results if "error" not in r)
    fp_drops = sum(
        1 for r in results if "error" not in r
        for d in r.get("drop_judgments") or []
        if d.get("supported", "") == "EVET"
    )
    partial_drops = sum(
        1 for r in results if "error" not in r
        for d in r.get("drop_judgments") or []
        if d.get("supported", "") == "KISMI"
    )
    correct_drops = sum(
        1 for r in results if "error" not in r
        for d in r.get("drop_judgments") or []
        if d.get("supported", "") == "HAYIR"
    )

    valid = [r for r in results if "error" not in r and (r.get("answer_judgment") or {}).get("score", 0) > 0]
    avg_answer_score = sum(r["answer_judgment"]["score"] for r in valid) / max(len(valid), 1)

    lines = []
    lines.append(f"# PaytarAI Mini Eval — {ts}\n")
    lines.append("## Ozet\n")
    lines.append(f"- **Soru sayisi**: {len(results)}\n")
    lines.append(f"- **Toplam droplanan cumle**: {total_drops}\n")
    lines.append(f"  - Halusinasyon (DOGRU drop): **{correct_drops}**\n")
    lines.append(f"  - Tam destekleniyor (YANLIS drop / false positive): **{fp_drops}**\n")
    lines.append(f"  - Kismi destekleniyor (kismi yanlis): **{partial_drops}**\n")
    if total_drops > 0:
        fp_rate = (fp_drops + partial_drops * 0.5) / total_drops * 100
        lines.append(f"  - **False positive orani**: {fp_rate:.1f}%\n")
    lines.append(f"- **Ortalama yanit kalitesi**: {avg_answer_score:.2f} / 5\n")
    lines.append("\n---\n")

    for r in results:
        q = r["q"]
        lines.append(f"\n## {q['id']} ({q['user_role']})\n")
        lines.append(f"**Soru**: {q['message']}\n\n")

        if "error" in r:
            lines.append(f"**HATA**: {r['error']}\n")
            continue

        data = r["data"]
        ans = r["answer_judgment"]
        lines.append(f"**Pipeline suresi**: {r['api_time_s']}s · {len(data['chunks'])} chunk · {len(data['dropped_sentences'])} cumle drop\n\n")

        lines.append(f"### Cevap kalitesi: **{ans['score']}/5**\n")
        lines.append(f"{ans['reason']}\n\n")

        # Final yanit
        lines.append("### Final yanit\n")
        lines.append(f"```\n{data['final_response']}\n```\n")

        # Droplanan cumleler + judge
        if r["drop_judgments"]:
            lines.append("### Droplanan cumleler (LettuceDetect)\n")
            for i, dj in enumerate(r["drop_judgments"], 1):
                marker = "✅ DOGRU" if dj["supported"] == "HAYIR" else ("❌ YANLIS" if dj["supported"] == "EVET" else "⚠ KISMI")
                lines.append(f"\n**#{i}** {marker} — judge: {dj['supported']}\n")
                lines.append(f"> {dj['sentence']}\n\n")
                lines.append(f"_Gerekce_: {dj['reason']}\n")
        else:
            lines.append("### Droplanan cumle yok ✓\n")

        # Chunk basliklari
        lines.append("\n### Generator'a giden chunklar\n")
        for i, c in enumerate(data["chunks"], 1):
            lines.append(f"- [{i}] [{c.get('language','?')}] **{c.get('title','?')}** — dense={c.get('dense_score','?')} · σ={c.get('rerank_sigmoid','?')}\n")

        lines.append("\n---\n")

    path.write_text("".join(lines), encoding="utf-8")
    print(f"\n{'='*90}")
    print(f"  RAPOR: {path}")
    print(f"{'='*90}")
    print(f"  Toplam drop: {total_drops}")
    print(f"    DOGRU drop (halluc): {correct_drops}")
    print(f"    YANLIS drop (false positive): {fp_drops}")
    print(f"    KISMI: {partial_drops}")
    print(f"  Ortalama cevap kalitesi: {avg_answer_score:.2f}/5")
    print(f"{'='*90}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
