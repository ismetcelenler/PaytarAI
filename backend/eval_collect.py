"""
Mini eval — sadece VERI toplar, hicbir LLM judge YOK.

Her soru icin: chunklar + cumleler (drop kararlariyla) + final yanit dump.
Insan (mühendis) raporu okuyup her cumleyi tek tek degerlendirir.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib import request

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

API_BASE = os.environ.get("PAYTAR_API", "http://localhost:8000")
RESEARCH_DIR = Path(__file__).parent.parent / "research"
RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

QUESTIONS = [
    {"id": "bloat",                "user_role": "veterinarian",
     "message": "Sığırlarda karın şişkinliği nedenleri nelerdir?"},
    {"id": "calf_diarrhea",        "user_role": "veterinarian",
     "message": "Yenidoğan buzağılarda ishal yapan başlıca etkenler ve ayırıcı tanı nasıldır?"},
    {"id": "postpartum",           "user_role": "producer",
     "message": "İneğim doğurduktan 5 gün sonra halsiz yürüyor ve sütü azaldı, ne yapayım?"},
    {"id": "milk_fever",           "user_role": "veterinarian",
     "message": "Süt humması (parturient paresis) patogenezi ve tedavisi nedir?"},
    {"id": "abomasal_displacement","user_role": "veterinarian",
     "message": "Şirden sola kayması (sol abomasal displasman) nasıl teşhis ve tedavi edilir?"},
]


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


def main() -> int:
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out_path = RESEARCH_DIR / f"eval_data_{ts}.md"
    lines: list[str] = []
    lines.append(f"# PaytarAI Eval Data — {ts}\n\n")
    lines.append("**Insan tarafindan elle degerlendirilecek**. Her cumle icin:\n")
    lines.append("- Drop EDILEN: hallüsinasyon mu (DOGRU) yoksa false positive mi (YANLIS)?\n")
    lines.append("- KORUNAN: gercekten chunklarda destekleniyor mu (DOGRU) yoksa kacirilan halusinasyon mu (YANLIS)?\n\n")
    lines.append("---\n\n")

    for i, q in enumerate(QUESTIONS, 1):
        print(f"\n[{i}/{len(QUESTIONS)}] {q['id']}: {q['message'][:60]}")
        t0 = time.time()
        try:
            api_resp = call_api(q)
        except Exception as e:
            print(f"  ✗ {e}")
            lines.append(f"## {q['id']} — HATA: {e}\n\n")
            continue
        elapsed = time.time() - t0

        trace = api_resp.get("debug_trace", [])
        chunks = []
        sentences = []
        draft_in = ""
        draft_out = ""

        for e in trace:
            if e.get("node") == "retriever":
                chunks = e.get("output", {}).get("reranked_top_k", []) or []
            elif e.get("node") == "sentence_grounding":
                draft_in = e.get("input", {}).get("draft_in", "")
                out = e.get("output", {}) or {}
                sentences = out.get("sentences", []) or []
                draft_out = out.get("draft_out", "")

        final_resp = api_resp.get("response", "")
        n_drop = sum(1 for s in sentences if not s.get("supported", True))

        print(f"  ✓ {elapsed:.0f}s · {len(chunks)} chunk · {len(sentences)} cumle · {n_drop} drop")

        lines.append(f"## SORU {i}: {q['id']} ({q['user_role']})\n\n")
        lines.append(f"**Kullanici sorusu**: {q['message']}\n\n")
        lines.append(f"**Pipeline**: {elapsed:.0f}s · {len(chunks)} chunk · {len(sentences)} cumle · **{n_drop} drop**\n\n")

        # CHUNKS — full text
        lines.append("### Generator'a giden chunklar\n\n")
        for j, c in enumerate(chunks, 1):
            lines.append(f"#### [Kaynak {j}] [{c.get('language','?')}] {c.get('title','?')}\n")
            lines.append(f"dense={c.get('dense_score')} · σ={c.get('rerank_sigmoid')} · {c.get('text_len','?')} char\n\n")
            lines.append(f"```\n{c.get('text_full','')}\n```\n\n")

        # SENTENCES with decisions
        lines.append("### Sentence Grounding karar tablosu\n\n")
        lines.append("| # | Karar | Halluc oran | Cumle |\n")
        lines.append("|---|---|---|---|\n")
        for j, s in enumerate(sentences, 1):
            decision = "🔴 DROP" if not s.get("supported", True) else "🟢 KEEP"
            ratio = s.get("hallucination_ratio", 0)
            text = (s.get("text", "") or "").replace("\n", " ").replace("|", "\\|")[:200]
            lines.append(f"| {j} | {decision} | {ratio:.0%} | {text} |\n")
        lines.append("\n")

        # Drop edilen cumleler (detayli)
        dropped = [s for s in sentences if not s.get("supported", True)]
        if dropped:
            lines.append("### Drop edilen cumlelerin halluc span detaylari\n\n")
            for j, s in enumerate(dropped, 1):
                lines.append(f"**Drop #{j}** (ratio %{s.get('hallucination_ratio',0)*100:.0f}):\n")
                lines.append(f"> {s.get('text','')}\n\n")
                for sp in s.get("hallucination_spans", []) or []:
                    conf = sp.get("confidence", 0) * 100
                    txt = sp.get("text", "")
                    lines.append(f"- _{conf:.0f}%_: `{txt}`\n")
                lines.append("\n")

        # Draft IN vs OUT
        lines.append("### Draft IN (generator ham)\n\n")
        lines.append(f"```\n{draft_in}\n```\n\n")
        lines.append("### Draft OUT (grounding sonrasi)\n\n")
        lines.append(f"```\n{draft_out}\n```\n\n")

        # Final
        lines.append("### Final yanit (kullaniciya giden)\n\n")
        lines.append(f"```\n{final_resp}\n```\n\n")
        lines.append("---\n\n")

    out_path.write_text("".join(lines), encoding="utf-8")
    print(f"\n{'='*90}")
    print(f"  Veri dump: {out_path}")
    print(f"{'='*90}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
