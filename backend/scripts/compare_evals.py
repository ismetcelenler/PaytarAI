"""
v2 baseline vs Phase 2 full50 — case-by-case detayli karsilastirma.

Aniliz hedefleri:
  1. Token rate limit isareti var mi (yuksek latency, error mesajlari)
  2. Hangi case'ler iki tarafta da fail, hangileri yeni fail
  3. Response uzunluk anomalileri (cok kisa/bos cevaplar)
  4. response_status / evidence_confidence dagilimi
  5. Latency outlier analizi
"""
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

V2_PATH = BASE_DIR / "eval/reports/20260520_024920__v2_baseline_hybrid.json"
P2_PATH = BASE_DIR / "eval/reports/20260521_102532__phase2_full50.json"


def load(path):
    return json.load(open(path, encoding="utf-8"))


def case_pass(c):
    """3 koşul: fact_llm>=0.67, forbidden OK, retrieval>=0.5"""
    m = c["metrics"]
    return (
        m["fact_coverage_llm"]["score"] >= 0.67
        and m["forbidden_check"]["passed"]
        and m["retrieval_precision"]["score"] >= 0.5
    )


def summarize(name, data):
    cases = data["results"]
    n = len(cases)
    print(f"\n{'='*70}\n{name}  (N={n})\n{'='*70}")

    # Latency dagilimi
    latencies = [float(c["latency_sec"]) for c in cases]
    print(f"Latency: min={min(latencies):.1f}s  max={max(latencies):.1f}s  "
          f"avg={sum(latencies)/n:.1f}s")
    # Outlier > 100s (rate limit retry isareti)
    outliers = [(c["id"], float(c["latency_sec"])) for c in cases if float(c["latency_sec"]) > 100]
    if outliers:
        print(f"  >100s outliers: {outliers}")

    # Response uzunluk
    resp_lens = [len(c["response"]) for c in cases]
    short = [(c["id"], len(c["response"])) for c in cases if len(c["response"]) < 300]
    print(f"Response length: min={min(resp_lens)}  max={max(resp_lens)}  "
          f"avg={sum(resp_lens)//n}")
    if short:
        print(f"  <300 char (cok kisa): {short}")

    # Status dagilimi
    statuses = {}
    for c in cases:
        s = c.get("response_status", "?")
        statuses[s] = statuses.get(s, 0) + 1
    print(f"Status: {statuses}")

    # Confidence dagilimi
    confs = {}
    for c in cases:
        cf = c.get("evidence_confidence", "?")
        confs[cf] = confs.get(cf, 0) + 1
    print(f"Confidence: {confs}")

    # Critic retry dagilimi
    retries = {}
    for c in cases:
        r = str(c.get("critic_attempts", "0"))
        retries[r] = retries.get(r, 0) + 1
    print(f"Critic retries: {retries}")

    # Error olan case'ler
    errors = [(c["id"], c.get("error")) for c in cases if c.get("error") and c["error"] != "None"]
    if errors:
        print(f"ERRORS: {errors}")

    # Rate limit / token isareti — response icinde "limit", "error", "429"
    suspect_text = []
    for c in cases:
        r = c["response"].lower()
        if any(kw in r for kw in ["rate limit", "429", "token", "context length",
                                    "max_tokens", "internal error", "api error"]):
            # Sadece response icinde — meta yorum degil
            suspect_text.append((c["id"], r[:100]))
    if suspect_text:
        print(f"  Suspect response content: {suspect_text}")

    return cases


def compare(v2, p2):
    v2_map = {c["id"]: c for c in v2["results"]}
    p2_map = {c["id"]: c for c in p2["results"]}

    common_ids = sorted(set(v2_map) & set(p2_map))

    print(f"\n{'='*70}\nCASE-BY-CASE COMPARISON  ({len(common_ids)} common case)\n{'='*70}")

    only_v2_pass = []  # v2 OK, p2 fail
    only_p2_pass = []  # p2 OK, v2 fail
    both_fail = []
    both_pass = 0
    latency_jumps = []  # Phase2 latency >> v2 latency

    for cid in common_ids:
        v2c = v2_map[cid]
        p2c = p2_map[cid]
        v2_ok = case_pass(v2c)
        p2_ok = case_pass(p2c)

        v2_lat = float(v2c["latency_sec"])
        p2_lat = float(p2c["latency_sec"])
        if p2_lat > v2_lat + 30 and p2_lat > 60:
            latency_jumps.append((cid, v2_lat, p2_lat))

        if v2_ok and p2_ok:
            both_pass += 1
        elif v2_ok and not p2_ok:
            only_v2_pass.append(cid)
        elif p2_ok and not v2_ok:
            only_p2_pass.append(cid)
        else:
            both_fail.append(cid)

    print(f"Both PASS:                {both_pass}")
    print(f"Both FAIL:                {len(both_fail)}  {both_fail}")
    print(f"v2 PASS, Phase2 FAIL:     {len(only_v2_pass)}  {only_v2_pass}")
    print(f"v2 FAIL, Phase2 PASS:     {len(only_p2_pass)}  {only_p2_pass}")

    if latency_jumps:
        print(f"\nLatency jumps (Phase2 cok daha yavas):")
        for cid, l1, l2 in latency_jumps:
            print(f"  {cid}: v2={l1:.1f}s -> p2={l2:.1f}s  (+{l2-l1:.1f}s)")

    return only_v2_pass, only_p2_pass, both_fail, v2_map, p2_map


def show_failed_cases(case_ids, v2_map, p2_map, label="REGRESSION"):
    """v2 PASS → Phase2 FAIL case'lerini detayli goster"""
    print(f"\n{'='*70}\n{label}  ({len(case_ids)} case)\n{'='*70}")
    for cid in case_ids:
        v2c = v2_map[cid]
        p2c = p2_map[cid]
        print(f"\n--- {cid} [{p2c['category']}/{p2c['writing_style']}/{p2c['user_role']}] ---")
        print(f"QUESTION: {p2c['question'][:200]}")
        print(f"\n  v2 baseline:")
        print(f"    fact_llm={v2c['metrics']['fact_coverage_llm']['score']:.2f}  "
              f"forbidden={'OK' if v2c['metrics']['forbidden_check']['passed'] else 'FAIL'}  "
              f"retrieval={v2c['metrics']['retrieval_precision']['score']:.2f}  "
              f"top_sim={v2c['metrics']['retrieval_precision'].get('top_score', 0):.3f}")
        print(f"    status={v2c['response_status']}  conf={v2c['evidence_confidence']}  "
              f"retries={v2c['critic_attempts']}  lat={float(v2c['latency_sec']):.1f}s  "
              f"resp_len={len(v2c['response'])}")

        print(f"\n  Phase 2:")
        print(f"    fact_llm={p2c['metrics']['fact_coverage_llm']['score']:.2f}  "
              f"forbidden={'OK' if p2c['metrics']['forbidden_check']['passed'] else 'FAIL'}  "
              f"retrieval={p2c['metrics']['retrieval_precision']['score']:.2f}  "
              f"top_sim={p2c['metrics']['retrieval_precision'].get('top_score', 0):.3f}")
        print(f"    status={p2c['response_status']}  conf={p2c['evidence_confidence']}  "
              f"retries={p2c['critic_attempts']}  lat={float(p2c['latency_sec']):.1f}s  "
              f"resp_len={len(p2c['response'])}")
        if not p2c['metrics']['forbidden_check']['passed']:
            print(f"    FORBIDDEN VIOLATIONS: {p2c['metrics']['forbidden_check']['violations']}")
        if p2c['metrics']['fact_coverage_llm']['score'] < 0.67:
            print(f"    LLM MISSED FACTS: {p2c['metrics']['fact_coverage_llm'].get('missed', [])}")


def main():
    v2 = load(V2_PATH)
    p2 = load(P2_PATH)

    summarize("v2 baseline (no reranker)", v2)
    summarize("Phase 2 (reranker + enrich-fix)", p2)

    only_v2, only_p2, both_fail, v2_map, p2_map = compare(v2, p2)

    show_failed_cases(only_v2, v2_map, p2_map, label="REGRESSIONS (v2 PASS -> Phase2 FAIL)")
    show_failed_cases(only_p2, v2_map, p2_map, label="IMPROVEMENTS (v2 FAIL -> Phase2 PASS)")
    show_failed_cases(both_fail, v2_map, p2_map, label="BOTH FAIL (zaten kotuydu)")


if __name__ == "__main__":
    main()
