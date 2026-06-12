"""
PaytarAI — OpenRouter 3-soru smoke test.

5 LLM cagrisi da OpenRouter'a tasindi:
  - scope_check, step_back, sentence_grounding -> llama-3.3-70b-instruct:free
  - generator, critic -> openai/gpt-oss-120b:free

3 farkli sorgu tipinde calistir, her cagri icin error/skip durumu raporla.
"""

from __future__ import annotations
import json
import os
import sys
import time
from urllib import request, error

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

API_BASE = os.environ.get("PAYTAR_API", "http://localhost:8000")

QUERIES = [
    {
        "id": "vet_neonatal",
        "user_role": "veterinarian",
        "message": "Yenidoğan buzağılarda ishal yapan başlıca etkenler nelerdir, ayırt edici özellikleri nedir?",
        "test_focus": "VET teknik soru — generator full reasoning + grounding aktif",
    },
    {
        "id": "producer_postpartum",
        "user_role": "producer",
        "message": "ineğim doğurdu 5 gün oldu sallak gibi yürüyor sütü de az ne yapayım",
        "test_focus": "Üretici broken style — sade Türkçe + grounding filter",
    },
    {
        "id": "out_of_scope_dog",
        "user_role": "producer",
        "message": "köpeğim ishal oldu ne yapayım",
        "test_focus": "Kapsam dışı — sadece scope_check çağrılmalı",
    },
]


def send(q: dict) -> dict:
    body = json.dumps({
        "message": q["message"],
        "user_role": q["user_role"],
        "input_source": "text",
        "debug": True,
        "thread_id": f"or-{q['id']}",
    }).encode("utf-8")
    req = request.Request(
        f"{API_BASE}/api/v1/chat",
        data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    with request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())


def summarize_trace(data: dict) -> list[str]:
    lines = []
    for entry in data.get("debug_trace", []):
        node = entry.get("node", "?")
        lat = entry.get("latency_ms", 0)
        out = entry.get("output", {}) or {}
        inp = entry.get("input", {}) or {}
        err = out.get("error")

        if node == "scope_check":
            dec = out.get("decision")
            hyde = len(out.get("hyde_variants") or [])
            lines.append(f"  scope_check {lat:.0f}ms · {dec} · hyde={hyde}")
        elif node == "retriever":
            scores = out.get("scores") or {}
            n_rerank = len(out.get("reranked_top_k") or [])
            lines.append(f"  retriever {lat:.0f}ms · dense={scores.get('dense_top'):.3f} rerank={scores.get('rerank_top'):.4f} top-{n_rerank}")
        elif node == "generator":
            cc = out.get("char_count", 0)
            model = out.get("model", "")
            if err:
                lines.append(f"  generator {lat:.0f}ms · ERROR: {err[:100]}")
            else:
                lines.append(f"  generator {lat:.0f}ms · {cc}ch · {model}")
        elif node == "sentence_grounding":
            stats = out.get("stats") or {}
            action = out.get("action") or "skip"
            if out.get("skipped"):
                lines.append(f"  grounding {lat:.0f}ms · SKIP/{out.get('reason') or err or 'unknown'}")
            else:
                lines.append(
                    f"  grounding {lat:.0f}ms · {action} · "
                    f"total={stats.get('total')} specific={stats.get('specific')} "
                    f"generic={stats.get('generic')} dropped={stats.get('dropped')} "
                    f"drop_ratio={stats.get('drop_ratio')}"
                )
        elif node == "critic":
            dec = out.get("decision")
            judge_ok = out.get("judge_ok")
            judge_err = out.get("judge_error")
            if judge_err:
                lines.append(f"  critic {lat:.0f}ms · {dec} · judge ERROR: {judge_err[:80]}")
            else:
                lines.append(f"  critic {lat:.0f}ms · {dec} · judge_ok={judge_ok}")
    return lines


def main() -> int:
    print()
    print("=" * 90)
    print("  OpenRouter 5-LLM Migration Smoke Test (3 sorgu)")
    print("=" * 90)
    print()

    overall = {"ok": 0, "fail": 0, "errors": []}

    for i, q in enumerate(QUERIES, 1):
        print(f"[{i}/{len(QUERIES)}] {q['id']} ({q['user_role']})")
        print(f"  Soru: {q['message'][:80]}")
        print(f"  Test odagi: {q['test_focus']}")
        t0 = time.time()
        try:
            data = send(q)
            elapsed = time.time() - t0
        except error.HTTPError as e:
            elapsed = time.time() - t0
            body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
            print(f"  ✗ HTTP {e.code} after {elapsed:.1f}s")
            print(f"    body: {body[:300]}")
            overall["fail"] += 1
            overall["errors"].append((q["id"], f"HTTP {e.code}"))
            print()
            continue
        except Exception as e:
            elapsed = time.time() - t0
            print(f"  ✗ {type(e).__name__}: {e}")
            overall["fail"] += 1
            overall["errors"].append((q["id"], str(e)[:100]))
            print()
            continue

        print(f"  ✓ {elapsed:.1f}s · conf={data.get('evidence_confidence')} attempts={data.get('critic_attempts')} grounding={data.get('grounding_action')}")
        for ln in summarize_trace(data):
            print(ln)

        resp = data.get("response", "")
        print(f"  Yanit ({len(resp)}ch): {resp[:200]}")
        print()
        overall["ok"] += 1

    print("=" * 90)
    print(f"  OZET: {overall['ok']}/{len(QUERIES)} basarili, {overall['fail']} hata")
    if overall["errors"]:
        print("  Hatalar:")
        for cid, err in overall["errors"]:
            print(f"    - {cid}: {err}")
    print("=" * 90)
    return 0 if overall["fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
