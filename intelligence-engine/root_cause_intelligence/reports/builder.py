"""RCI markdown report — Top 10 clusters + recommended PRs."""

from __future__ import annotations

from typing import Any


def build_markdown(analysis: dict[str, Any]) -> str:
    lines = [
        "# AGIB Root Cause Intelligence — Analysis Report",
        "",
        f"**Analysis ID:** `{analysis.get('analysis_id')}`  ",
        f"**IEL run:** `{analysis.get('iel_run_id')}`  ",
        f"**Suite:** `{analysis.get('iel_suite')}`  ",
        f"**Commit:** `{analysis.get('iel_commit')}`  ",
        f"**RCI version:** `{analysis.get('version')}`  ",
        "",
        "## Headline",
        "",
        f"- IEL pass %: **{analysis.get('iel_pass_pct')}** (target 95%+)",
        f"- Failures: **{analysis.get('n_failures')}** across **{analysis.get('n_clusters')}** clusters",
        f"- Framework accuracy proxy: **{(analysis.get('kpi_proxies') or {}).get('framework_accuracy_pct')}%** (target 98%+)",
        f"- Intent accuracy proxy: **{(analysis.get('kpi_proxies') or {}).get('intent_accuracy_pct')}%** (target 99%+)",
        "",
        "## Gaps to stop condition",
        "",
    ]
    for k, v in (analysis.get("gaps") or {}).items():
        lines.append(f"- `{k}`: **{v}**")
    lines += ["", "## Top 10 failure clusters", ""]
    for i, c in enumerate(analysis.get("top_10_clusters") or [], 1):
        fix = c.get("suggested_fix") or {}
        lines += [
            f"### {i}. {c.get('impact_statement')}",
            "",
            f"- Cluster ID: `{c.get('cluster_id')}`",
            f"- Key: `{c.get('cluster_key')}`",
            f"- Severity: **{c.get('severity')}** · Owner: `{c.get('owner')}`",
            f"- Expected frameworks: `{c.get('expected_frameworks_sample')}`",
            f"- Actual frameworks: `{c.get('actual_frameworks_sample')}`",
            f"- Suggested fix: **{fix.get('title')}**",
            f"- Recommended branch: `{fix.get('recommended_branch')}`",
            f"- PR brief: {fix.get('pr_brief')}",
            "",
        ]
    lines += ["## Recommended PRs (engineering queue)", ""]
    for i, pr in enumerate(analysis.get("recommended_prs") or [], 1):
        lines += [
            f"{i}. **{pr.get('title')}** (`{pr.get('recommended_branch')}`) — impact {pr.get('count')} Qs",
            f"   - Files: {', '.join(pr.get('files') or [])}",
            f"   - Next sprint: {pr.get('next_sprint')}",
            "",
        ]
    lines += [
        "## Engineering loop",
        "",
        "```text",
        "Git Commit → 1,025 Questions → Judges → RCI → Top 10 Clusters → Recommended PR → Engineer → Benchmark Again",
        "```",
        "",
        "Do not fix individual question IDs. Fix clusters.",
        "",
    ]
    return "\n".join(lines)
