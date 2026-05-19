"""
PaytarAI Eval Runner

Kullanim (backend/ dizininden):
    python -m eval.run_eval                              # default dataset
    python -m eval.run_eval --dataset eval/datasets/eval_set.yaml
    python -m eval.run_eval --limit 3                    # ilk 3 soruyu kostur
    python -m eval.run_eval --tag baseline               # rapor adina etiket

Cikti:
    eval/reports/<timestamp>__<tag>.json   — ham sonuclar
    eval/reports/<timestamp>__<tag>.md     — okunabilir ozet
"""

# OpenMP/MKL conflict onleyici — MUTLAKA en basta
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import sys
from pathlib import Path

# backend/ sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# KRITIK: embeddings (FlagEmbedding/torch) langgraph'tan ONCE yuklenmeli.
# Aksi halde native lib cakismasi nedeniyle segfault olusur.
from app.rag import embeddings  # noqa: E402, F401

import argparse  # noqa: E402
import json  # noqa: E402
import time  # noqa: E402
import traceback  # noqa: E402
from datetime import datetime  # noqa: E402

import yaml  # noqa: E402

from app.graph.workflow import get_workflow  # noqa: E402
from eval.metrics.fact_coverage import fact_coverage  # noqa: E402
from eval.metrics.forbidden import must_not_contain  # noqa: E402
from eval.metrics.retrieval import retrieval_precision  # noqa: E402
from eval.metrics.latency import latency_seconds  # noqa: E402
from eval.metrics.llm_judge import fact_coverage_llm  # noqa: E402
from eval.report import write_markdown_report  # noqa: E402


DEFAULT_DATASET = BACKEND_DIR / "eval" / "datasets" / "eval_set.yaml"
REPORTS_DIR = BACKEND_DIR / "eval" / "reports"


def _get_messages_from_case(case: dict) -> list[dict]:
    """
    Eval case'inden mesaj listesi cikarir.
    - Multi-turn: case["messages"] kullanilir (assistant turn'leri dahil)
    - Single-turn: case["question"] tek user mesaji olarak sarilir
    """
    if "messages" in case and case["messages"]:
        return [
            {"role": m["role"], "content": m["content"]}
            for m in case["messages"]
        ]
    return [{"role": "user", "content": case["question"]}]


def _get_user_question_for_judge(case: dict) -> str:
    """LLM judge icin asil kullanici sorusunu cikarir (son user turn'u)."""
    if "messages" in case and case["messages"]:
        for m in reversed(case["messages"]):
            if m.get("role") == "user":
                return m["content"]
        return ""
    return case.get("question", "")


def _build_initial_state(case: dict) -> dict:
    """Eval case'inden AgentState'i kurar (single-turn ve multi-turn)."""
    return {
        "messages": _get_messages_from_case(case),
        "retrieved_docs": [],
        "tool_outputs": {},
        "thread_memory": {},
        "critic_attempts": 0,
        "compression_summary": "",
        "response_status": "",
        "user_role": case.get("user_role", "producer"),
        "input_source": "text",
        "evidence_confidence": "insufficient",
        "audit_log": [],
        "draft_response": "",
        "critic_rejection_reasons": [],
        "final_response": "",
        "request_id": f"eval-{case['id']}",
        "active_model": "",
        "retrieval_similarity_score": 0.0,
        "source_agreement": False,
        "dosage_triplet_validated": False,
        "source_trust_level": 5,
    }


def run_case(workflow, case: dict) -> dict:
    """Tek bir case'i kostur, tum metrikleri hesapla."""
    initial = _build_initial_state(case)

    with latency_seconds() as t:
        try:
            result = workflow.invoke(initial)
            error = None
        except Exception as e:
            traceback.print_exc()
            result = initial
            error = f"{type(e).__name__}: {e}"

    response_text = result.get("final_response", "") or result.get("draft_response", "")
    docs = result.get("retrieved_docs", [])

    facts = fact_coverage(response_text, case.get("expected_facts", []))
    user_question = _get_user_question_for_judge(case)
    facts_llm = fact_coverage_llm(response_text, case.get("expected_facts", []), user_question)
    forbidden = must_not_contain(response_text, case.get("must_not_contain", []))
    retrieval = retrieval_precision(
        docs,
        case.get("expected_sources", []) or [],
        top_k=3,
        expect_retrieval_fail=bool(case.get("expect_retrieval_fail", False)),
    )

    return {
        "id": case["id"],
        "category": case.get("category", ""),
        "writing_style": case.get("writing_style", "unknown"),
        "user_role": case.get("user_role", "producer"),
        "question": user_question,  # multi-turn icin son user mesaji, single icin tek soru
        "response": response_text,
        "response_status": result.get("response_status", ""),
        "critic_attempts": result.get("critic_attempts", 0),
        "active_model": result.get("active_model", ""),
        "evidence_confidence": result.get("evidence_confidence", ""),
        "latency_sec": t["seconds"],
        "metrics": {
            "fact_coverage": facts,
            "fact_coverage_llm": facts_llm,
            "forbidden_check": forbidden,
            "retrieval_precision": retrieval,
        },
        "error": error,
    }


def aggregate(results: list[dict]) -> dict:
    """Genel ozet skoru ve kategori kirilimi."""
    n = len(results)
    if n == 0:
        return {"n": 0}

    avg_fact = sum(r["metrics"]["fact_coverage"]["score"] for r in results) / n
    avg_fact_llm = sum(r["metrics"]["fact_coverage_llm"]["score"] for r in results) / n
    avg_retrieval = sum(r["metrics"]["retrieval_precision"]["score"] for r in results) / n
    avg_top_score = sum(r["metrics"]["retrieval_precision"]["top_score"] for r in results) / n
    forbidden_pass = sum(1 for r in results if r["metrics"]["forbidden_check"]["passed"])
    avg_latency = sum(r["latency_sec"] for r in results) / n
    errors = sum(1 for r in results if r["error"])

    def _aggregate_subset(items: list[dict]) -> dict:
        k = len(items)
        if k == 0:
            return {"n": 0}
        return {
            "n": k,
            "fact_coverage_avg": round(sum(i["metrics"]["fact_coverage"]["score"] for i in items) / k, 3),
            "fact_coverage_llm_avg": round(sum(i["metrics"]["fact_coverage_llm"]["score"] for i in items) / k, 3),
            "forbidden_pass_rate": round(sum(1 for i in items if i["metrics"]["forbidden_check"]["passed"]) / k, 3),
            "retrieval_precision_avg": round(sum(i["metrics"]["retrieval_precision"]["score"] for i in items) / k, 3),
            "top_sim_avg": round(sum(i["metrics"]["retrieval_precision"]["top_score"] for i in items) / k, 3),
        }

    # Kategori bazli
    by_category: dict[str, list[dict]] = {}
    for r in results:
        by_category.setdefault(r["category"], []).append(r)
    cat_summary = {cat: _aggregate_subset(items) for cat, items in by_category.items()}

    # writing_style bazli (stratified evaluation)
    by_style: dict[str, list[dict]] = {}
    for r in results:
        by_style.setdefault(r.get("writing_style", "unknown"), []).append(r)
    style_summary = {style: _aggregate_subset(items) for style, items in by_style.items()}

    # Robustness gap: clean - broken
    robustness_gap = None
    if "clean" in style_summary and "broken" in style_summary:
        clean_score = style_summary["clean"].get("fact_coverage_llm_avg", 0)
        broken_score = style_summary["broken"].get("fact_coverage_llm_avg", 0)
        robustness_gap = round(clean_score - broken_score, 3)

    return {
        "n": n,
        "fact_coverage_avg": round(avg_fact, 3),
        "fact_coverage_llm_avg": round(avg_fact_llm, 3),
        "forbidden_pass_rate": round(forbidden_pass / n, 3),
        "retrieval_precision_avg": round(avg_retrieval, 3),
        "retrieval_top_score_avg": round(avg_top_score, 3),
        "latency_sec_avg": round(avg_latency, 3),
        "errors": errors,
        "by_category": cat_summary,
        "by_writing_style": style_summary,
        "robustness_gap_clean_vs_broken": robustness_gap,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="PaytarAI eval runner")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET), help="Eval YAML path")
    parser.add_argument("--limit", type=int, default=0, help="Sadece ilk N case'i kostur (0 = hepsi)")
    parser.add_argument("--tag", default="run", help="Rapor dosyalarinda gorunecek etiket")
    parser.add_argument("--sleep", type=float, default=0.0, help="Case'ler arasi bekleme (saniye)")
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"[HATA] Dataset bulunamadi: {dataset_path}")
        return 1

    with dataset_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    cases = data.get("cases", [])
    if args.limit > 0:
        cases = cases[: args.limit]

    print(f"[Eval] {len(cases)} case kosturulacak — model: gpt-oss-120b (medium reasoning) @ Cerebras")
    workflow = get_workflow()

    results = []
    for idx, case in enumerate(cases, 1):
        q_preview = _get_user_question_for_judge(case)[:60]
        print(f"\n[{idx}/{len(cases)}] {case['id']} | {case.get('category', '')} | {q_preview}")
        r = run_case(workflow, case)
        results.append(r)

        m = r["metrics"]
        print(
            f"   fact_str={m['fact_coverage']['score']:.2f} "
            f"fact_llm={m['fact_coverage_llm']['score']:.2f} "
            f"forbidden={'OK' if m['forbidden_check']['passed'] else 'FAIL'} "
            f"retrieval={m['retrieval_precision']['score']:.2f} "
            f"top_sim={m['retrieval_precision']['top_score']:.2f} "
            f"latency={r['latency_sec']:.1f}s"
        )
        if r["error"]:
            print(f"   ERROR: {r['error']}")

        if args.sleep > 0 and idx < len(cases):
            time.sleep(args.sleep)

    summary = aggregate(results)
    print("\n" + "=" * 70)
    print(f"OZET: n={summary['n']}  "
          f"fact_str={summary['fact_coverage_avg']:.3f}  "
          f"fact_llm={summary['fact_coverage_llm_avg']:.3f}  "
          f"forbidden_pass={summary['forbidden_pass_rate']:.3f}  "
          f"retrieval={summary['retrieval_precision_avg']:.3f}  "
          f"top_sim={summary['retrieval_top_score_avg']:.3f}  "
          f"lat={summary['latency_sec_avg']:.1f}s")

    # Writing style stratified kırılım (varsa)
    style_summary = summary.get("by_writing_style", {})
    if style_summary and any(s != "unknown" for s in style_summary):
        print("\nYAZIM STILI KIRILIMI:")
        for style in ("clean", "mid", "broken", "unknown"):
            if style in style_summary:
                s = style_summary[style]
                print(f"  {style:8s} n={s['n']:>2d}  "
                      f"fact_llm={s.get('fact_coverage_llm_avg', 0):.3f}  "
                      f"forbidden={s.get('forbidden_pass_rate', 0):.3f}  "
                      f"top_sim={s.get('top_sim_avg', 0):.3f}")
        gap = summary.get("robustness_gap_clean_vs_broken")
        if gap is not None:
            print(f"  ROBUSTNESS GAP (clean - broken) = {gap:+.3f}")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = f"{ts}__{args.tag}"

    json_path = REPORTS_DIR / f"{stem}.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump({"summary": summary, "results": results}, f, ensure_ascii=False, indent=2)

    md_path = REPORTS_DIR / f"{stem}.md"
    write_markdown_report(md_path, summary, results, dataset_name=dataset_path.name, tag=args.tag)

    print(f"\nRapor: {md_path.relative_to(BACKEND_DIR)}")
    print(f"JSON : {json_path.relative_to(BACKEND_DIR)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
