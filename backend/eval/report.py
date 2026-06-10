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
    lines.append(f"| Forbidden pass rate | **{summary.get('forbidden_pass_rate', 0):.3f}** |")
    lines.append(f"| Retrieval precision (top-3 avg) | **{summary.get('retrieval_precision_avg', 0):.3f}** |")
    lines.append(f"| Avg top similarity score | {summary.get('retrieval_top_score_avg', 0):.3f} |")
    lines.append(f"| Avg latency | {summary.get('latency_sec_avg', 0):.2f} s |")
    lines.append("")

    cat = summary.get("by_category", {})
    if cat:
        lines.append("## Kategori Kirilimi")
        lines.append("")
        lines.append("| Kategori | N | Fact (str) | Forbidden | Retrieval | Top sim |")
        lines.append("|---|---|---|---|---|---|")
        for name, c in sorted(cat.items()):
            lines.append(
                f"| {name} | {c['n']} | {c.get('fact_coverage_avg', 0):.2f} | "
                f"{c['forbidden_pass_rate']:.2f} | {c['retrieval_precision_avg']:.2f} | "
                f"{c.get('top_sim_avg', 0):.2f} |"
            )
        lines.append("")

    # Writing style kırılımı (stratified evaluation)
    style = summary.get("by_writing_style", {})
    if style and any(s != "unknown" for s in style):
        lines.append("## Yazim Stili Kirilimi (Robustness)")
        lines.append("")
        lines.append("| Stil | N | Fact (str) | Forbidden | Retrieval | Top sim |")
        lines.append("|---|---|---|---|---|---|")
        for st in ("clean", "mid", "broken", "unknown"):
            if st in style:
                c = style[st]
                lines.append(
                    f"| **{st}** | {c['n']} | {c.get('fact_coverage_avg', 0):.2f} | "
                    f"{c.get('forbidden_pass_rate', 0):.2f} | {c.get('retrieval_precision_avg', 0):.2f} | "
                    f"{c.get('top_sim_avg', 0):.2f} |"
                )
        gap = summary.get("robustness_gap_clean_vs_broken")
        if gap is not None:
            lines.append("")
            lines.append(f"**Robustness gap top_sim (clean - broken):** `{gap:+.3f}`")
            if abs(gap) < 0.05:
                lines.append("Sistem yazim gurultusune dayanikli (gap < 0.05)")
            elif gap > 0.15:
                lines.append("Sistem temiz yazimda belirgin daha iyi (gap > 0.15) — embedder/retrieval iyilestirme aday")
            else:
                lines.append("Orta seviye dayaniklilik")
        lines.append("")

    lines.append("## Case Detaylari")
    lines.append("")
    for r in results:
        m = r["metrics"]
        forbidden_ok = "OK" if m["forbidden_check"]["passed"] else "FAIL"
        retrieval_ok = "OK" if m["retrieval_precision"]["score"] >= 0.66 else "ZAYIF"

        style_tag = f" [{r['writing_style']}]" if r.get("writing_style") and r["writing_style"] != "unknown" else ""
        lines.append(f"### `{r['id']}` — {r['category']} ({r['user_role']}){style_tag}")
        lines.append("")
        lines.append(f"**Soru:** {r['question']}")
        lines.append("")
        fact_ok = "OK" if m["fact_coverage"]["score"] >= 0.66 else "ZAYIF"
        lines.append(
            f"- **Fact (string): {m['fact_coverage']['score']:.2f} [{fact_ok}]** "
            f"(matched {len(m['fact_coverage']['matched'])}/{len(m['fact_coverage']['matched']) + len(m['fact_coverage']['missed'])})"
        )
        if m["fact_coverage"]["missed"]:
            lines.append(f"   - Kacirdi: {m['fact_coverage']['missed']}")
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
        chunks = r.get("retrieved_chunks") or []
        if chunks:
            lines.append("**Retrieved Chunks (top-5):**")
            lines.append("")
            lines.append("| # | Source | Lang | Dense | Rerank | Snippet |")
            lines.append("|---|---|---|---|---|---|")
            for c in chunks:
                snippet = c["snippet"].replace("\n", " ").replace("|", "\\|")
                if len(snippet) > 220:
                    snippet = snippet[:220] + "..."
                lines.append(
                    f"| {c['rank']} | {c['source'][:32]} | {c['language']} | "
                    f"{c['dense_score']:.3f} | {c['rerank_score']:.3f} | {snippet} |"
                )
            lines.append("")

        lines.append("**Yanit:**")
        lines.append("")
        lines.append("> " + (r["response"] or "(bos)").replace("\n", "\n> "))
        lines.append("")
        lines.append("---")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
