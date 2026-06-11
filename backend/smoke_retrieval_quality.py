"""
PaytarAI — Retrieval Quality Smoke Test

12 case (fixed_mini.yaml) icin sadece RETRIEVAL sinyallerini olcer:
  - max dense cosine skor (dense kanali: konu yakinligi)
  - max rerank score (cross-encoder: cevap chunkta var mi)
  - rerank logit (sigmoid kalibrasyon hatasini bypass eden gercek siralama skoru)

Fact_coverage gibi metin-eslesmesi metrikleri YOK. Sadece kaynak-cekim
kalitesi raporlar — generator iyi kaynak gormezse halusinasyon kacinilmaz,
o yuzden once burayi olcuyoruz.

Kullanim (backend zaten ayakta olmali):
  cd backend
  .\.venv\Scripts\python.exe smoke_retrieval_quality.py
  .\.venv\Scripts\python.exe smoke_retrieval_quality.py --dataset eval/datasets/fixed_quick.yaml
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


def ping() -> bool:
    try:
        with request.urlopen(f"{API_BASE}/", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def send_chat(case: dict) -> dict[str, Any]:
    # multi-turn varsa son user mesajini al, yoksa question
    msgs = case.get("messages", [])
    if msgs:
        user_msg = ""
        for m in reversed(msgs):
            if m.get("role") == "user":
                user_msg = m.get("content", "")
                break
    else:
        user_msg = case.get("question", "")

    body = json.dumps({
        "message": user_msg,
        "user_role": case.get("user_role", "producer"),
        "input_source": "text",
        "thread_id": f"retrqual-{case['id']}",
    }).encode("utf-8")

    req = request.Request(
        f"{API_BASE}/api/v1/chat",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


# audit reason "...dense_top=0.7747, rerank_top=0.1982" → float'a parse
_DENSE_RE = re.compile(r"dense_top=([\d.]+)")
_RERANK_RE = re.compile(r"rerank_top=([\d.]+)")


def extract_retrieval(data: dict) -> tuple[float, float, str]:
    """audit_log'tan dense_top + rerank_top + ilk source title cek."""
    for entry in data.get("audit_log", []):
        if entry.get("action") == "retrieval_done":
            reason = str(entry.get("reason", ""))
            d = _DENSE_RE.search(reason)
            r = _RERANK_RE.search(reason)
            dense = float(d.group(1)) if d else 0.0
            rerank = float(r.group(1)) if r else 0.0
            top_src = ""
            sources = data.get("sources", [])
            if sources:
                top_src = sources[0].get("title", "")[:30]
            return dense, rerank, top_src
    return 0.0, 0.0, "(retrieval atlandi - out of scope mu?)"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
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

    print(f"Dataset: {ds}")
    print(f"Cases: {len(cases)}")
    print(f"Backend: {API_BASE}")
    print()

    hdr = (
        f"{'#':>2}  {'ID':<22} {'Cat':<18} {'Style':<7} {'Dense':>6} "
        f"{'Rerank':>7} {'Time':>6}  Top source"
    )
    print(hdr)
    print("─" * 110)

    rows: list[dict] = []
    for i, case in enumerate(cases, 1):
        cid = case["id"][:22]
        cat = (case.get("category") or "")[:18]
        style = (case.get("writing_style") or "")[:7]
        t0 = time.time()
        try:
            resp = send_chat(case)
            dense, rerank, top_src = extract_retrieval(resp)
            elapsed = time.time() - t0
        except error.HTTPError as e:
            print(f"{i:>2}  {cid:<22} {cat:<18} {style:<7}  HTTP {e.code}")
            continue
        except Exception as e:
            elapsed = time.time() - t0
            print(f"{i:>2}  {cid:<22} {cat:<18} {style:<7}  ERR {type(e).__name__}: {str(e)[:30]}")
            continue

        row = {
            "id": case["id"],
            "category": case.get("category", ""),
            "style": case.get("writing_style", ""),
            "dense_top": dense,
            "rerank_top": rerank,
            "latency_s": elapsed,
            "top_src": top_src,
            "is_oos": cat in ("oos", "out_of_scope") or "out" in cat.lower(),
        }
        rows.append(row)

        print(
            f"{i:>2}  {cid:<22} {cat:<18} {style:<7} "
            f"{dense:>6.3f} {rerank:>7.4f} {elapsed:>5.1f}s  {top_src}"
        )

    # ─────────────────────────────────────────────────────────
    # Aggregates
    # ─────────────────────────────────────────────────────────
    print()
    print("=" * 110)
    print("OZET")
    print("=" * 110)

    # OOS case'leri ayir — retrieval skoru beklenmez
    in_scope = [r for r in rows if not r["is_oos"]]
    oos = [r for r in rows if r["is_oos"]]

    def _stats(items: list[dict], label: str) -> None:
        if not items:
            print(f"  {label}: (yok)")
            return
        n = len(items)
        dense_avg = sum(r["dense_top"] for r in items) / n
        rerank_avg = sum(r["rerank_top"] for r in items) / n
        lat_avg = sum(r["latency_s"] for r in items) / n
        dense_min = min(r["dense_top"] for r in items)
        dense_max = max(r["dense_top"] for r in items)
        rr_min = min(r["rerank_top"] for r in items)
        rr_max = max(r["rerank_top"] for r in items)
        print(f"  {label}: n={n}")
        print(f"    dense_top  : avg={dense_avg:.3f}  min={dense_min:.3f}  max={dense_max:.3f}")
        print(f"    rerank_top : avg={rerank_avg:.4f}  min={rr_min:.4f}  max={rr_max:.4f}")
        print(f"    latency    : avg={lat_avg:.1f}s")

    _stats(in_scope, "IN-SCOPE")
    _stats(oos, "OUT-OF-SCOPE (retrieval atlanan)")

    # Kategori bazli rerank ortalamasi
    print()
    print("  Kategori bazli rerank_top ortalamasi (in-scope):")
    by_cat: dict[str, list[float]] = {}
    for r in in_scope:
        by_cat.setdefault(r["category"], []).append(r["rerank_top"])
    for cat, vals in sorted(by_cat.items()):
        avg = sum(vals) / len(vals)
        print(f"    {cat:<22} n={len(vals)}  rerank_avg={avg:.4f}")

    # Stil bazli (clean/mid/broken)
    print()
    print("  Stil bazli rerank_top ortalamasi (in-scope):")
    by_style: dict[str, list[float]] = {}
    for r in in_scope:
        by_style.setdefault(r["style"], []).append(r["rerank_top"])
    for style, vals in sorted(by_style.items()):
        avg = sum(vals) / len(vals)
        print(f"    {style:<10} n={len(vals)}  rerank_avg={avg:.4f}")

    # Düsük rerank case'leri — "cevap chunkta yok" riski
    print()
    print("  ⚠ Düsük rerank_top (<0.15) case'leri — generator halusinasyon riski:")
    risky = [r for r in in_scope if r["rerank_top"] < 0.15]
    if not risky:
        print("    (yok — tum case'lerde rerank yeterli)")
    else:
        for r in risky:
            print(f"    {r['id']:<22} rerank={r['rerank_top']:.4f} dense={r['dense_top']:.3f} src={r['top_src']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
