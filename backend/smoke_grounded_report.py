"""
PaytarAI — Grounded Check Report

Her case icin yan yana: soru | top-3 chunk (rerank sirali) | generator yaniti
Markdown rapor uretir. Kullanici gözüyle "yanit chunklardan mi geldi" sorusunu
hizla cevaplayabilir.

Kullanim (backend ayakta olmali):
  cd backend
  .\.venv\Scripts\python.exe smoke_grounded_report.py
  Cikti: smoke_grounded_report.md
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib import request, error

import yaml

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

API_BASE = os.environ.get("PAYTAR_API", "http://localhost:8000")
DEFAULT_DATASET = "eval/datasets/fixed_mini.yaml"
DEFAULT_OUT = "smoke_grounded_report.md"


def ping() -> bool:
    try:
        with request.urlopen(f"{API_BASE}/", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def get_user_msg(case: dict) -> str:
    msgs = case.get("messages", [])
    if msgs:
        for m in reversed(msgs):
            if m.get("role") == "user":
                return m.get("content", "")
    return case.get("question", "")


def send_chat(case: dict) -> dict[str, Any]:
    user_msg = get_user_msg(case)
    body = json.dumps({
        "message": user_msg,
        "user_role": case.get("user_role", "producer"),
        "input_source": "text",
        "thread_id": f"grounded-{case['id']}",
    }).encode("utf-8")
    req = request.Request(
        f"{API_BASE}/api/v1/chat",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


_DENSE_RE = re.compile(r"dense_top=([\d.]+)")
_RERANK_RE = re.compile(r"rerank_top=([\d.]+)")


def get_retrieval_signals(data: dict) -> tuple[float, float]:
    for entry in data.get("audit_log", []):
        if entry.get("action") == "retrieval_done":
            reason = str(entry.get("reason", ""))
            d = _DENSE_RE.search(reason)
            r = _RERANK_RE.search(reason)
            return (float(d.group(1)) if d else 0.0, float(r.group(1)) if r else 0.0)
    return 0.0, 0.0


def critic_summary(data: dict) -> str:
    actions = [e.get("action", "") for e in data.get("audit_log", [])]
    # genelde: critic_accepted | critic_rejected | critic_safe_fallback | critic_max_retries | confidence_skip_oos
    critic_actions = [a for a in actions if "critic" in a or "scope" in a or "confidence" in a]
    return " → ".join(critic_actions) if critic_actions else "(yok)"


def render_case(case: dict, data: dict) -> str:
    """Tek case icin markdown bolumu uretir."""
    cid = case["id"]
    cat = case.get("category", "?")
    style = case.get("writing_style", "?")
    role = case.get("user_role", "?")
    question = get_user_msg(case)
    response = data.get("response", "")
    sources = data.get("sources", [])
    dense, rerank = get_retrieval_signals(data)
    crit = critic_summary(data)
    conf = data.get("evidence_confidence", "?")
    attempts = data.get("critic_attempts", 0)
    expected = case.get("expected_facts", [])

    md = []
    md.append(f"\n---\n")
    md.append(f"## `{cid}`  ·  {cat}  ·  {style}  ·  {role}\n")
    md.append(f"**Signals**: dense_top=`{dense:.3f}` · rerank_top=`{rerank:.4f}` · confidence=`{conf}` · attempts=`{attempts}`  ")
    md.append(f"\n**Critic chain**: `{crit}`\n")

    md.append(f"\n### ❓ Soru\n")
    md.append(f"> {question}\n")

    if expected:
        md.append(f"\n### 🎯 Beklenen kavramlar (eval YAML)\n")
        for ef in expected:
            md.append(f"- `{ef}`")
        md.append("\n")

    md.append(f"\n### 📚 Generator'a giden top-3 chunk (rerank sıralı)\n")
    if not sources:
        md.append("*(chunk yok — out-of-scope veya retrieval atlandı)*\n")
    else:
        for i, src in enumerate(sources, 1):
            title = src.get("title", "?")
            score = src.get("score", 0.0)
            snippet = src.get("snippet", "").strip()
            # Çift boşluk ve newline temizle (markdown blockquote için)
            snippet = re.sub(r"\s+", " ", snippet)
            md.append(f"\n**Chunk [{i}]** — `{title}` · dense_score=`{score:.3f}`\n")
            md.append(f"\n> {snippet}\n")

    md.append(f"\n### 💬 Generator yanıtı\n")
    md.append(f"\n{response}\n")

    return "".join(md)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    if not ping():
        print(f"✗ Backend {API_BASE} ulasilamiyor.")
        return 1

    ds = Path(args.dataset)
    if not ds.exists():
        print(f"✗ Dataset bulunamadi: {ds}")
        return 1

    with ds.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    cases = data.get("cases", [])
    if args.limit > 0:
        cases = cases[: args.limit]

    out_path = Path(args.out)
    print(f"Dataset: {ds}")
    print(f"Cases: {len(cases)}")
    print(f"Backend: {API_BASE}")
    print(f"Output: {out_path}")
    print()

    sections: list[str] = []
    sections.append(f"# PaytarAI — Grounded Check Report\n")
    sections.append(
        f"\nDataset: `{ds.name}`  ·  Cases: `{len(cases)}`  ·  Backend: `{API_BASE}`\n"
    )
    sections.append(
        f"\nHer case icin: **top-3 chunk** (generator'a giden, rerank sirali) "
        f"ile **generator yaniti** yan yana. Yanitin chunk'lardan ne kadar "
        f"dogrudan turetildigini eyeball kontrol icin.\n"
    )

    for i, case in enumerate(cases, 1):
        cid = case["id"]
        print(f"[{i}/{len(cases)}] {cid} ... ", end="", flush=True)
        t0 = time.time()
        try:
            resp = send_chat(case)
            elapsed = time.time() - t0
            md = render_case(case, resp)
            sections.append(md)
            dense, rerank = get_retrieval_signals(resp)
            print(f"OK  dense={dense:.3f} rerank={rerank:.4f} {elapsed:.1f}s")
        except error.HTTPError as e:
            elapsed = time.time() - t0
            print(f"HTTP {e.code}")
            sections.append(f"\n---\n## `{cid}`\n\n**HATA**: HTTP {e.code}\n")
        except Exception as e:
            elapsed = time.time() - t0
            print(f"ERR {type(e).__name__}")
            sections.append(f"\n---\n## `{cid}`\n\n**HATA**: {type(e).__name__}: {e}\n")

    out_path.write_text("".join(sections), encoding="utf-8")
    print()
    print(f"✓ Rapor yazildi: {out_path}")
    print(f"  Boyut: {out_path.stat().st_size:,} byte")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
