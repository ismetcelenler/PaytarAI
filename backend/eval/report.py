"""Markdown rapor uretici."""

from pathlib import Path


def write_markdown_report(out_path: Path, summary: dict, results: list[dict], dataset_name: str, tag: str) -> None:
    """Eval sonuclarini okunabilir markdown rapor olarak yazar."""
    lines: list[str] = []
    lines.append(f"# PaytarAI Eval Raporu — {tag}")
    lines.append("")
    lines.append(f"- Dataset: `{dataset_name}`")
    lines.append(f"- Case sayisi: **{summary.get('n', 0)}**")
    lines.append(f"- Hata sayisi: {summary.get('errors', 0)}")
    lines.append("")
    lines.append("## Ozet Skorlar")
    lines.append("")
    lines.append("| Metrik | Deger |")
    lines.append("|---|---|")
    lines.append(f"| Fact coverage — string match (avg) | {summary.get('fact_coverage_avg', 0):.3f} |")
    lines.append(f"| **Fact coverage — LLM judge (avg)** | **{summary.get('fact_coverage_llm_avg', 0):.3f}** |")
    lines.append(f"| Forbidden pass rate | **{summary.get('forbidden_pass_rate', 0):.3f}** |")
    lines.append(f"| Retrieval precision (top-3 avg) | **{summary.get('retrieval_precision_avg', 0):.3f}** |")
    lines.append(f"| Avg top similarity score | {summary.get('retrieval_top_score_avg', 0):.3f} |")
    lines.append(f"| Avg latency | {summary.get('latency_sec_avg', 0):.2f} s |")
    lines.append("")

    cat = summary.get("by_category", {})
    if cat:
        lines.append("## Kategori Kirilimi")
        lines.append("")
        lines.append("| Kategori | N | Fact cov | Forbidden pass | Retrieval |")
        lines.append("|---|---|---|---|---|")
        for name, c in sorted(cat.items()):
            lines.append(
                f"| {name} | {c['n']} | {c['fact_coverage_avg']:.2f} | "
                f"{c['forbidden_pass_rate']:.2f} | {c['retrieval_precision_avg']:.2f} |"
            )
        lines.append("")

    lines.append("## Case Detaylari")
    lines.append("")
    for r in results:
        m = r["metrics"]
        forbidden_ok = "OK" if m["forbidden_check"]["passed"] else "FAIL"
        retrieval_ok = "OK" if m["retrieval_precision"]["score"] >= 0.66 else "ZAYIF"

        lines.append(f"### `{r['id']}` — {r['category']} ({r['user_role']})")
        lines.append("")
        lines.append(f"**Soru:** {r['question']}")
        lines.append("")
        lines.append(
            f"- Fact (string): {m['fact_coverage']['score']:.2f} "
            f"(matched {len(m['fact_coverage']['matched'])}/{len(m['fact_coverage']['matched']) + len(m['fact_coverage']['missed'])})"
        )
        llm_ok = "OK" if m["fact_coverage_llm"]["score"] >= 0.66 else "ZAYIF"
        lines.append(
            f"- **Fact (LLM judge): {m['fact_coverage_llm']['score']:.2f} [{llm_ok}]** "
            f"(matched {len(m['fact_coverage_llm']['matched'])}/{len(m['fact_coverage_llm']['matched']) + len(m['fact_coverage_llm']['missed'])})"
        )
        if m["fact_coverage_llm"]["missed"]:
            lines.append(f"   - LLM kacirdi: {m['fact_coverage_llm']['missed']}")
        lines.append(f"- Forbidden: **[{forbidden_ok}]** — ihlal: {m['forbidden_check']['violations'] or '-'}")
        lines.append(
            f"- Retrieval: **{m['retrieval_precision']['score']:.2f}** [{retrieval_ok}] "
            f"top_sim={m['retrieval_precision']['top_score']:.2f}"
        )
        lines.append(
            f"- Pipeline: status={r['response_status']}  "
            f"critic_retries={r['critic_attempts']}  "
            f"confidence={r['evidence_confidence']}  "
            f"latency={r['latency_sec']:.2f}s"
        )
        if r.get("error"):
            lines.append(f"- **ERROR:** {r['error']}")
        lines.append("")
        lines.append("**Yanit:**")
        lines.append("")
        lines.append("> " + (r["response"] or "(bos)").replace("\n", "\n> "))
        lines.append("")
        lines.append("---")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
