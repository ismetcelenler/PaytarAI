"""
PaytarAI — Context size profiler

Tum LLM cagrilarinda hangi prompt'lar hangi buyuklukte gidiyor? Bir sorgu
calistirir, debug_trace'ten her node'un input_size (char + ~token) cikartip
tablolar.

Token tahmini: chars / 3.5 (Turkce icin ortalama char-per-token; OpenAI
tiktoken cl100k base TR'de 3.3-3.8 araliginda doner; 3.5 makul ortalama).
"""

import json
import os
import sys
from urllib import request

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

API_BASE = os.environ.get("PAYTAR_API", "http://localhost:8000")
CHARS_PER_TOKEN = 3.5


def fetch_trace(message: str, role: str = "veterinarian") -> dict:
    body = json.dumps({
        "message": message,
        "user_role": role,
        "input_source": "text",
        "debug": True,
    }).encode("utf-8")
    req = request.Request(
        f"{API_BASE}/api/v1/chat", data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    with request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())


def fmt(n: int) -> str:
    return f"{n:>6,}".replace(",", ".")


def main():
    queries = [
        ("Holstein'da klinik mastitis nasil ayirt edilir?", "veterinarian"),
        ("ineğim doğurdu 5 gün oldu sallak gibi yürüyor sütü de az ne yapayım", "producer"),
    ]

    print()
    print("=" * 110)
    print("  PAYTAR-AI — Pipeline LLM Context Sizes")
    print("=" * 110)
    print()
    print("  Note: char = harf say, tok ≈ char/3.5 (TR ortalama)")
    print()

    for q, role in queries:
        print(f"\n▸ Sorgu ({role}): {q[:70]}...")
        try:
            data = fetch_trace(q, role)
        except Exception as e:
            print(f"  HATA: {e}")
            continue
        trace = data.get("debug_trace", [])

        rows = []
        for entry in trace:
            node = entry.get("node", "?")
            inp = entry.get("input", {}) or {}
            out = entry.get("output", {}) or {}
            lat = entry.get("latency_ms", 0)

            # Bir node'da birden fazla LLM cagri olabilir (orn. critic + judge,
            # generator + reasoning). Her node icin input'taki "prompt benzeri"
            # alanlari toplayalim.

            if node == "scope_check":
                # query_analyzer prompt = ANALYZER_PROMPT(~1.5K) + query
                # Ama tracede sadece user_message tutuluyor. Statik prompt + query.
                user_msg = inp.get("user_message", "") or ""
                # ANALYZER_PROMPT statik kismi ~1500 char
                static = 1500
                total = static + len(user_msg)
                raw_out = out.get("raw_analyzer", "") or ""
                rows.append({
                    "node": "scope_check",
                    "llm": "Groq llama-3.3-70b-versatile",
                    "prompt_static": static,
                    "prompt_dynamic": len(user_msg),
                    "prompt_total": total,
                    "output_chars": len(raw_out),
                    "latency_ms": lat,
                })

            elif node == "retriever":
                # step_back LLM cagri retriever'in icinde. Trace'te step_back_query var.
                # STEP_BACK_PROMPT statik ~700 char + user query.
                step_back_q = inp.get("step_back_query", "") or ""
                user_q = inp.get("user_query", "") or ""
                if step_back_q:
                    rows.append({
                        "node": "step_back",
                        "llm": "Groq llama-3.3-70b-versatile",
                        "prompt_static": 700,
                        "prompt_dynamic": len(user_q),
                        "prompt_total": 700 + len(user_q),
                        "output_chars": len(step_back_q),
                        "latency_ms": "(retriever içi)",
                    })
                # Plus rerank passes — cross-encoder (yerel torch, LLM degil)

            elif node == "generator":
                system_p = inp.get("system_prompt", "") or ""
                context_m = inp.get("context_msg", "") or ""
                raw = out.get("raw_response", "") or ""
                rows.append({
                    "node": "generator",
                    "llm": "Cerebras gpt-oss-120b (med reasoning)",
                    "prompt_static": len(system_p),
                    "prompt_dynamic": len(context_m),
                    "prompt_total": len(system_p) + len(context_m),
                    "output_chars": len(raw),
                    "latency_ms": lat,
                })

            elif node == "sentence_grounding":
                prompt = inp.get("prompt", "") or ""
                draft_in = inp.get("draft_in", "") or ""
                raw_llm = out.get("raw_llm", "") or ""
                # prompt = GROUNDING_PROMPT (~2K static) + sources (~3K) + draft (~3K)
                # Tracede prompt zaten composite tutuluyor (chunk_count'a bagli)
                rows.append({
                    "node": "sentence_grounding",
                    "llm": "Groq llama-3.3-70b-versatile",
                    "prompt_static": 2000,  # GROUNDING_PROMPT statik
                    "prompt_dynamic": len(prompt) - 2000 if len(prompt) > 2000 else len(prompt),
                    "prompt_total": len(prompt),
                    "output_chars": len(raw_llm),
                    "latency_ms": lat,
                })

            elif node == "critic":
                jp = out.get("judge_prompt", "") or ""
                jraw = out.get("judge_raw_response", "") or ""
                # Critic her cagrida 1 judge LLM call yapiyor
                rows.append({
                    "node": "critic (judge)",
                    "llm": "Cerebras gpt-oss-120b (low reasoning)",
                    "prompt_static": 2500,  # JUDGE_PROMPT statik
                    "prompt_dynamic": len(jp) - 2500 if len(jp) > 2500 else len(jp),
                    "prompt_total": len(jp),
                    "output_chars": len(jraw),
                    "latency_ms": lat,
                })

        # Tablo bas
        print()
        hdr = (
            f"  {'node':<22} {'provider':<42} "
            f"{'prompt(c)':>10} {'≈tok':>6} {'output(c)':>10} {'≈tok':>6} {'latency':>10}"
        )
        print(hdr)
        print("  " + "─" * 108)
        for r in rows:
            tot = r["prompt_total"]
            outc = r["output_chars"]
            print(
                f"  {r['node']:<22} {r['llm']:<42} "
                f"{fmt(tot)} {int(tot / CHARS_PER_TOKEN):>6} "
                f"{fmt(outc)} {int(outc / CHARS_PER_TOKEN):>6} "
                f"{str(r['latency_ms']):>10}"
            )

        # Toplam
        total_prompt = sum(r["prompt_total"] for r in rows)
        total_output = sum(r["output_chars"] for r in rows)
        print("  " + "─" * 108)
        print(
            f"  {'TOTAL':<22} {'':<42} "
            f"{fmt(total_prompt)} {int(total_prompt / CHARS_PER_TOKEN):>6} "
            f"{fmt(total_output)} {int(total_output / CHARS_PER_TOKEN):>6}"
        )

    print()
    print("=" * 110)
    print("  Provider bazli toplam (yukaridaki 2 sorgu)")
    print("=" * 110)
    print()
    print("  Bir query'de tetiklenen LLM cagrilari:")
    print("    Groq llama-3.3-70b-versatile :  3 cagri (scope_check + step_back + grounding)")
    print("    Cerebras gpt-oss-120b        :  2 cagri (generator + critic-judge)")
    print()
    print("  Critic retry'da generator ve critic tekrar calisir → +2 Cerebras cagri")
    print("  Grounding skip ederse 1 Groq cagri eksilir")


if __name__ == "__main__":
    raise SystemExit(main())
