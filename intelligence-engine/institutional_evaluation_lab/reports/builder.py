"""IEL report builder — markdown + structured summary."""

from __future__ import annotations

from typing import Any


def build_markdown_report(summary: dict[str, Any]) -> str:
    agg = summary.get("aggregate") or {}
    clusters = summary.get("failure_clusters") or {}
    reg = summary.get("regression") or {}
    targets = summary.get("targets") or {}
    lines = [
        "# AGIB Institutional Evaluation Lab — Run Report",
        "",
        f"**Run ID:** `{summary.get('run_id')}`  ",
        f"**Suite:** `{summary.get('suite')}`  ",
        f"**Mode:** `{summary.get('mode')}`  ",
        f"**Commit:** `{summary.get('commit')}`  ",
        f"**IEL version:** `{summary.get('iel_version')}`  ",
        "",
        "## Aggregate",
        "",
        f"| Metric | Value |",
        f"|--------|------:|",
        f"| Questions | {agg.get('n')} |",
        f"| Pass % | {agg.get('pass_pct')} |",
        f"| Mean score | {agg.get('mean_score')} |",
        f"| Passed | {agg.get('passed')} |",
        f"| Failed | {agg.get('failed')} |",
        "",
        "## Regression",
        "",
        f"- Status: **{reg.get('status')}**",
        f"- Deltas: `{reg.get('deltas')}`",
        "",
        "## Category means",
        "",
    ]
    for cat, meta in (agg.get("by_category") or {}).items():
        lines.append(f"- **{cat}**: {meta.get('mean_score')} (n={meta.get('n')})")
    lines += ["", "## Top root causes", ""]
    for c in (agg.get("top_root_causes") or [])[:12]:
        lines.append(f"- `{c.get('cause')}` — {c.get('count')}")
    lines += ["", "## Failure clusters (top 10)", ""]
    for c in (clusters.get("top_20") or [])[:10]:
        lines.append(
            f"- **{c.get('root_cause')}** (n={c.get('count')}, severity={c.get('severity')}) "
            f"cats={c.get('categories')}"
        )
    lines += ["", "## Distance to Quality Programme targets", ""]
    bp = targets.get("benchmark_1000_pass_pct") or {}
    if bp.get("observed") is not None:
        lines.append(
            f"- 1000-Q pass %: observed **{bp.get('observed')}** / target **{bp.get('target')}** "
            f"(gap {bp.get('gap')})"
        )
    fw = targets.get("framework_selection_proxy") or {}
    if fw.get("observed") is not None:
        lines.append(
            f"- Framework selection proxy: observed **{fw.get('observed')}** / "
            f"target **{fw.get('target')}**"
        )
    lines += [
        "",
        "## Programme note",
        "",
        "Every sprint must start with a measured weakness and end with a measurable improvement. "
        "IEL is the measurement system that protects AGIB from feature theatre.",
        "",
    ]
    return "\n".join(lines)
