"""
PaytarAI — Pipeline Smoke Test (HTTP-tabanli)

Calisma sekli:
  Bu script, ZATEN AYAGA KALKMIS bir backend'e (default: http://localhost:8000)
  HTTP istekleri atar ve donen audit_log + sources + response icerigini
  analiz eder. In-process invoke nativ segfault verdigi icin (Windows + torch),
  bunun yerine API yuzunden butun pipeline'i sinariz.

  Backend onceden ayri bir terminal'de calismali:
    uvicorn app.main:app --reload --port 8000

Kullanim:
  cd backend
  .\.venv\Scripts\python.exe smoke_pipeline.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any
from urllib import request, error

# UTF-8 stdout (Windows cp1254 crashine karsi)
sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

API_BASE = os.environ.get("PAYTAR_API", "http://localhost:8000")

# ─────────────────────────────────────────────────────────────
SCENARIOS = [
    {
        "id": "vet_mastitis",
        "label": "VET kapsam ici, kuvvetli soru (mastitis)",
        "user_role": "veterinarian",
        "message": "Holstein'da klinik mastitis nasil ayirt edilir?",
        "expected": "in_scope, kaliteli retrieval, accepted yanit",
    },
    {
        "id": "vet_asilama_HALLUCINATION_CASE",
        "label": "VET asilama takvimi (bilinen halusinasyon case'i)",
        "user_role": "veterinarian",
        "message": "Suru asilama takvimi 2026 Turkiye",
        "expected": "Yeni sertlestirilmis prompt _INSUFFICIENT_VET sablonuna dusmeli",
    },
    {
        "id": "out_of_scope_dog",
        "label": "Kapsam disi (kopek)",
        "user_role": "producer",
        "message": "Kopegim ishal oldu ne yapayim",
        "expected": "out_of_scope, generator/critic atlanir",
    },
]

HALLUCINATION_TRIGGERS = [
    "Brucella", "Theileria", "Pasteurella", "Manhaemia", "Mannheimia",
    "BVD", "BRSV", "IBR", "PI3", "klostridial", "Mart-Nisan",
    "S19", "J-5", "cefquinome",
]


# ─────────────────────────────────────────────────────────────
def hr(c: str = "─", w: int = 80) -> None:
    print(c * w)


def section(title: str) -> None:
    print()
    hr("═")
    print(f"  {title}")
    hr("═")


def subsection(title: str) -> None:
    print()
    hr()
    print(f"  ▸ {title}")
    hr()


# ─────────────────────────────────────────────────────────────
def ping() -> bool:
    try:
        req = request.Request(f"{API_BASE}/", method="GET")
        with request.urlopen(req, timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def send_chat(message: str, user_role: str, thread_id: str) -> dict[str, Any]:
    body = json.dumps({
        "message": message,
        "user_role": user_role,
        "input_source": "text",
        "thread_id": thread_id,
    }).encode("utf-8")
    req = request.Request(
        f"{API_BASE}/api/v1/chat",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


# ─────────────────────────────────────────────────────────────
def run_scenario(s: dict[str, Any]) -> dict[str, Any]:
    section(f"[{s['id']}] {s['label']}")
    print(f"  Soru:     {s['message']}")
    print(f"  Rol:      {s['user_role']}")
    print(f"  Beklenti: {s['expected']}")

    t0 = time.time()
    try:
        data = send_chat(s["message"], s["user_role"], f"smoke-{s['id']}")
        elapsed = time.time() - t0
    except error.HTTPError as e:
        elapsed = time.time() - t0
        body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        print(f"\n  !! HTTP {e.code}: {body[:300]}")
        return {"scenario": s["id"], "ok": False, "elapsed_s": elapsed, "error": str(e)}
    except Exception as e:
        elapsed = time.time() - t0
        print(f"\n  !! EXCEPTION: {type(e).__name__}: {e}")
        return {"scenario": s["id"], "ok": False, "elapsed_s": elapsed, "error": str(e)}

    # ── Audit timeline (geçen süreler ile)
    subsection(f"Audit timeline (toplam {elapsed:.2f}s)")
    audit = data.get("audit_log", [])
    if not audit:
        print("  (audit_log bos — backend audit_log return etmiyor olabilir)")
    else:
        prev_ts = None
        for entry in audit:
            ts_full = entry.get("timestamp", "")
            ts_short = ts_full[-15:-6] if ts_full else "         "
            action = entry.get("action", "?")
            model = entry.get("model_used", "")
            reason = entry.get("reason") or ""
            if isinstance(reason, list):
                reason = "; ".join(reason)
            reason = str(reason)
            conf = entry.get("evidence_confidence", "")

            delta = ""
            if prev_ts and ts_full:
                try:
                    from datetime import datetime
                    a = datetime.fromisoformat(prev_ts)
                    b = datetime.fromisoformat(ts_full)
                    delta = f"+{(b - a).total_seconds() * 1000:>5.0f}ms"
                except Exception:
                    delta = ""
            prev_ts = ts_full

            print(f"  {ts_short}  {delta:<10}  {action:<26}  conf={conf}")
            if model:
                print(f"               model:  {model}")
            if reason:
                print(f"               reason: {reason[:230]}")

    # ── Final state ozeti
    subsection("Final state")
    resp = data.get("response", "")
    conf = data.get("evidence_confidence", "")
    attempts = data.get("critic_attempts", 0)
    sources = data.get("sources", [])
    print(f"  evidence_confidence:   {conf}")
    print(f"  critic_attempts:       {attempts}")
    print(f"  sources returned:      {len(sources)}")
    for i, src in enumerate(sources[:5]):
        title = src.get("title", "?")
        score = src.get("score", 0.0)
        print(f"    [{i+1}] {title:<40} score={score:.3f}")

    # ── Retrieval breakdown — audit reason'undan parse et
    subsection("Retrieval channel breakdown")
    retrieval_entry = next((e for e in audit if e.get("action") == "retrieval_done"), None)
    if retrieval_entry:
        reason = str(retrieval_entry.get("reason", ""))
        # "candidates=47 (orig=30, enriched=0, hyde_variants=3 [N chunks], step_back=yes [30 chunks], bm25=30), reranked_top_k=3, dense_top=0.768, rerank_top=0.198"
        for piece in reason.split(","):
            print(f"  {piece.strip()}")
    else:
        print("  (retrieval_done audit yok)")

    # ── Tum reranked chunk'larin SNIPPET dump'i — soruyu CEVAPLIYOR mu kontrol icin
    subsection("Reranked top chunks (snippet)")
    if not sources:
        print("  (chunk yok)")
    else:
        for i, src in enumerate(sources):
            print(f"  --- [{i+1}] {src.get('title', '?')} score={src.get('score', 0):.3f} ---")
            snippet = src.get("snippet", "").replace("\n", " ")
            # 350 karakter göster (snippet default 200, ama bazen daha uzun)
            print(f"  {snippet[:350]}")
            if len(snippet) > 350:
                print(f"  ...")

    # ── Response preview
    subsection("Response (ilk 500 char)")
    for line in resp[:500].splitlines():
        print(f"  {line}")
    if len(resp) > 500:
        print(f"  ... ({len(resp) - 500} char daha, toplam {len(resp)})")

    # ── Halusinasyon kontrolu: bilinen tetikleyici kelimeler yanitta var mi
    # ama kaynak snippet'inde yok mu?
    triggered: list[str] = []
    if s["user_role"] == "veterinarian":
        sources_blob = " ".join(src.get("snippet", "") for src in sources).lower()
        for kw in HALLUCINATION_TRIGGERS:
            if kw.lower() in resp.lower() and kw.lower() not in sources_blob:
                triggered.append(kw)

    if triggered:
        subsection("⚠ HALUSINASYON SINYALI")
        print(f"  Bu terimler YANITTA var ama KAYNAKLARDA (snippet) yok:")
        for kw in triggered:
            print(f"    - {kw}")
        print("  -> Generator hala kaynak-disi spesifik iddialar yaziyor.")
        print("     NOT: snippet kisitli (~200 char/kaynak); kaynak metnin tamaminda")
        print("     terim gecebilir. False positive olabilir.")
    elif s["id"] == "vet_asilama_HALLUCINATION_CASE":
        subsection("✓ Halusinasyon kontrolu temiz")
        print("  Daha onceki halusinasyon tetikleyicileri yanitta gorulmedi.")

    return {
        "scenario": s["id"],
        "ok": True,
        "elapsed_s": elapsed,
        "confidence": conf,
        "attempts": attempts,
        "n_sources": len(sources),
        "audit_actions": [e.get("action") for e in audit],
        "hallucination_triggers": triggered,
        "response_chars": len(resp),
    }


# ─────────────────────────────────────────────────────────────
def main() -> int:
    section("PaytarAI Pipeline Smoke Test (HTTP)")
    print(f"  Target: {API_BASE}")
    print(f"  Scenarios: {len(SCENARIOS)}")
    print(f"  Note: critic atlanan yerler:")
    print(f"    - response_status=='fallback' (savunulabilir)")
    print(f"    - after_retriever top_sim<0.60 (savunulabilir)")
    print(f"    - LLM-judge silent fail (KRITIK BUG, fail-closed olmali)")

    subsection("Backend ping")
    if not ping():
        print(f"  ✗ {API_BASE} ulasilamiyor.")
        print(f"    Once backend'i baska terminalde baslat:")
        print(f"    cd backend; .\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --port 8000")
        return 1
    print(f"  ✓ {API_BASE} aktif.")

    results = []
    for s in SCENARIOS:
        try:
            r = run_scenario(s)
            results.append(r)
        except KeyboardInterrupt:
            print("\n[interrupted]")
            break
        except Exception as exc:
            print(f"\n  !! Scenario crash: {exc}")
            import traceback
            traceback.print_exc()
            results.append({"scenario": s["id"], "ok": False, "error": str(exc)})

    # Ozet tablo
    section("OZET")
    print(f"  {'Senaryo':<38} {'Conf':<8} {'Atts':>4} {'Sources':>8} {'Time':>7}  Halu?")
    hr()
    for r in results:
        if not r.get("ok"):
            print(f"  {r['scenario']:<38} CRASH   -      -       {r.get('elapsed_s', 0):.2f}s  -")
            continue
        halu_flag = f"YES ({len(r['hallucination_triggers'])})" if r.get("hallucination_triggers") else "no"
        print(
            f"  {r['scenario']:<38} {r['confidence']:<8} {r['attempts']:>4} {r['n_sources']:>8} "
            f"{r['elapsed_s']:5.2f}s  {halu_flag}"
        )

    # Critic atlandi mi kontrolu
    subsection("Critic geçti mi?")
    for r in results:
        if not r.get("ok"):
            continue
        actions = r.get("audit_actions", [])
        critic_seen = any("critic" in a for a in actions)
        gen_seen = any("generator" in a for a in actions)
        if not gen_seen:
            print(f"  {r['scenario']:<38} → generator atlandi (workflow gate)")
        elif not critic_seen:
            print(f"  {r['scenario']:<38} ✗ GENERATOR cikti AMA CRITIC YOK — bug!")
        else:
            print(f"  {r['scenario']:<38} ✓ critic akisinda")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
