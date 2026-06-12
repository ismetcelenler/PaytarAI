"""
PaytarAI — Pattern 2 ile YENI sorular smoke test.

Eval setinde OLMAYAN, gercekci kullanici sorulariyla test eder. Pattern 2
(sentence_grounding) cumle cumle filtreleme yapinca yanitin halusinasyon
icermedigini ama useful KALDIGINI gormek icin.

Cikti: markdown rapor + audit timeline.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from urllib import request

import yaml

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

API_BASE = os.environ.get("PAYTAR_API", "http://localhost:8000")


# Eval setinde olmayan, paytar icin gercek diyaloglarla benzer 6 sorgu
NEW_QUERIES = [
    {
        "id": "new_01_neonatal_diarrhea_vet",
        "user_role": "veterinarian",
        "question": "Yenidoğan buzağılarda ishal yapan başlıca etkenler nelerdir, ayırt edici özellikleri nedir?",
        "test_focus": "Vet teknik — Rebhun's/Buzagi Sagligi'nde ayırıcı tanı var",
    },
    {
        "id": "new_02_producer_postpartum",
        "user_role": "producer",
        "question": "ineğim doğurdu 5 gün oldu sallak gibi yürüyor sütü de az ne yapayım",
        "test_focus": "Üretici broken style — süt humması patogenezi chunk'larında var",
    },
    {
        "id": "new_03_tympani_emergency",
        "user_role": "producer",
        "question": "ineğim aniden çok şişti karın bölgesi balon gibi ne yapayım acil mi",
        "test_focus": "Acil — Amasya DSYB timpani var ama spesifik tedavi (trokar) chunk'a bağlı",
    },
    {
        "id": "new_04_mastitis_vet_specific",
        "user_role": "veterinarian",
        "question": "Klinik mastitis tedavisinde intramammar antibiyotik seçiminde neye dikkat etmeli, atılım süresi nasıl yönetilir?",
        "test_focus": "Vet spesifik — intramammar antibiyotik atılım süresi muhtemelen kaynakta YOK → halüsinasyon riski",
    },
    {
        "id": "new_05_calf_vaccination",
        "user_role": "producer",
        "question": "buzağılarımı kaç günlükken aşılatmalıyım hangi aşılar gerekli",
        "test_focus": "Üretici — spesifik aşı takvimi (önceki halüsinasyon source'u). Pattern 2 yakalamalı.",
    },
    {
        "id": "new_06_reproductive_management",
        "user_role": "producer",
        "question": "ineğimi ne zaman tohumlatmalıyım uygun kızgınlık belirtileri nelerdir",
        "test_focus": "Üretici management — Pratik Sigircilik/Sut Sigirlarinin Bakimi'nda olmali",
    },
]


def send_chat(q: dict) -> dict:
    body = json.dumps({
        "message": q["question"],
        "user_role": q["user_role"],
        "input_source": "text",
        "thread_id": f"newq-{q['id']}",
    }).encode("utf-8")
    req = request.Request(
        f"{API_BASE}/api/v1/chat",
        data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    with request.urlopen(req, timeout=240) as r:
        return json.loads(r.read())


def main() -> int:
    print(f"Pattern 2 Smoke Test — {len(NEW_QUERIES)} yeni soru")
    print(f"Backend: {API_BASE}")
    print()

    out_path = "smoke_new_questions.md"
    sections: list[str] = ["# Pattern 2 — Yeni Sorular Test\n\n"]

    for i, q in enumerate(NEW_QUERIES, 1):
        print(f"[{i}/{len(NEW_QUERIES)}] {q['id']}", flush=True)
        t0 = time.time()
        try:
            data = send_chat(q)
            elapsed = time.time() - t0
        except Exception as e:
            print(f"  ERR: {e}")
            sections.append(f"\n## `{q['id']}`\n**ERROR**: {e}\n\n---\n")
            continue

        # audit'tan critic chain + grounding info cikar
        audit = data.get("audit_log", [])
        chain = " → ".join(
            e.get("action", "?") for e in audit
            if any(k in e.get("action", "") for k in ("scope", "grounding", "critic", "confidence"))
        )
        grounding_entry = next((e for e in audit if e.get("action") == "grounding_done"), None)
        retrieval_entry = next((e for e in audit if e.get("action") == "retrieval_done"), None)

        grounding_info = ""
        if grounding_entry:
            grounding_info = str(grounding_entry.get("reason", ""))
        elif any(e.get("action") == "grounding_safe_fallback" for e in audit):
            sf = next(e for e in audit if e.get("action") == "grounding_safe_fallback")
            grounding_info = f"SAFE_FALLBACK: {sf.get('reason', '')}"
        elif any(e.get("action") == "grounding_skip" for e in audit):
            sk = next(e for e in audit if e.get("action") == "grounding_skip")
            grounding_info = f"SKIP: {sk.get('reason', '')}"

        retrieval_info = ""
        if retrieval_entry:
            reason = str(retrieval_entry.get("reason", ""))
            d = re.search(r"dense_top=([\d.]+)", reason)
            r_ = re.search(r"rerank_top=([\d.]+)", reason)
            retrieval_info = f"dense={d.group(1) if d else '?'}, rerank={r_.group(1) if r_ else '?'}"

        sources = data.get("sources", [])
        resp = data.get("response", "")

        print(f"   time={elapsed:.1f}s  {retrieval_info}")
        print(f"   chain: {chain}")
        if grounding_info:
            safe = grounding_info.encode("ascii", "replace").decode("ascii")[:160]
            print(f"   grounding: {safe}")
        print(f"   conf={data.get('evidence_confidence', '?')}, attempts={data.get('critic_attempts', 0)}")
        print()

        # MD rapor
        sections.append(f"\n## `{q['id']}` · {q['user_role']}\n\n")
        sections.append(f"**Test odagi**: {q['test_focus']}\n\n")
        sections.append(f"**Sinyaller**: {retrieval_info}, conf=`{data.get('evidence_confidence')}`, attempts=`{data.get('critic_attempts')}`, time=`{elapsed:.1f}s`\n\n")
        sections.append(f"**Critic chain**: `{chain}`\n\n")
        if grounding_info:
            sections.append(f"**Grounding**: `{grounding_info[:200]}`\n\n")

        sections.append(f"### Soru\n> {q['question']}\n\n")

        sections.append(f"### Top-3 chunk (rerank sirali)\n")
        for j, src in enumerate(sources, 1):
            title = src.get("title", "?")
            score = src.get("score", 0)
            snippet = re.sub(r"\s+", " ", src.get("snippet", "")).strip()
            sections.append(f"\n**[{j}]** `{title}` (score=`{score:.3f}`)\n\n> {snippet[:600]}\n")

        sections.append(f"\n### Generator yaniti\n\n{resp}\n\n---\n")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("".join(sections))
    print(f"\n✓ Rapor: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
