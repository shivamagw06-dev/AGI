"""Institutional Evaluation Report formatter."""

from __future__ import annotations

from typing import Any


def format_institutional_evaluation_report(pack: dict[str, Any]) -> str:
    """Render the Phase 1 Institutional Evaluation Report (human-readable)."""
    gov = pack.get("governance") or {}
    ev = pack.get("evidence") or {}
    dq = pack.get("decision_quality") or {}
    drift = pack.get("drift") or {}
    op = pack.get("operational") or {}
    uni = pack.get("universe") or {}
    overall = pack.get("overall") or {}

    def _v(x: Any, suffix: str = "") -> str:
        if x is None:
            return "n/a"
        return f"{x}{suffix}"

    lines = [
        "==========================================================",
        "AGIB Phase 1 Institutional Evaluation Report",
        "==========================================================",
        "",
        f"Release",
        "",
        f"{pack.get('release_id')}",
        "",
        f"Architecture",
        "",
        f"{pack.get('architecture_version')}",
        "",
        f"Golden Universe",
        "",
        f"{uni.get('companies', pack.get('companies_tested'))} companies",
        "",
        "==========================================================",
        "",
        "Governance",
        "",
        f"{gov.get('status')}",
        "",
        "Constitution",
        "",
        f"{_v(gov.get('constitution_pct'), '%')}",
        "",
        "Spec Compliance",
        "",
        f"{_v(gov.get('spec_compliance_pct'), '%')}",
        "",
        "Editorial Violations",
        "",
        f"{gov.get('editorial_violations')}",
        "",
        "==========================================================",
        "",
        "Evidence",
        "",
        "Coverage",
        "",
        f"{_v(ev.get('coverage_pct'), '%')}",
        "",
        "Freshness",
        "",
        f"{_v(ev.get('freshness_pct'), '%')}",
        "",
        "Institutional Readiness",
        "",
        f"{_v(ev.get('institutional_readiness_pct'), '%')}",
        "",
        "==========================================================",
        "",
        "Decision Quality",
        "",
        "Average Company Quality",
        "",
        f"{_v(dq.get('average_company_quality'))}",
        "",
        "Average Opportunity",
        "",
        f"{_v(dq.get('average_opportunity'))}",
        "",
        "Average Readiness",
        "",
        f"{_v(dq.get('average_recommendation_readiness_pct'), '%')}",
        "",
        "Average Confidence",
        "",
        f"{_v(dq.get('average_analytical_confidence_pct'), '%')}",
        "",
        "==========================================================",
        "",
        "Drift",
        "",
        "Recommendation Changes",
        "",
        f"{drift.get('recommendation_changes')}",
        "",
        "Expected",
        "",
        f"{drift.get('expected')}",
        "",
        "Unexpected",
        "",
        f"{drift.get('unexpected')}",
        "",
        "==========================================================",
        "",
        "Performance",
        "",
        "Average Runtime",
        "",
        f"{_v(op.get('average_runtime_s'), ' s')}",
        "",
        "95th Percentile",
        "",
        f"{_v(op.get('p95_runtime_s'), ' s')}",
        "",
        "==========================================================",
        "",
        "Overall Result",
        "",
        f"{overall.get('status')}",
        "",
    ]
    if overall.get("status") == "PASS":
        lines += [
            "AGIB Phase 1 qualifies as the production baseline.",
            "",
        ]
    else:
        reasons = overall.get("fail_reasons") or []
        lines += [
            "AGIB Phase 1 does NOT qualify as the production baseline.",
            "",
        ]
        if reasons:
            lines.append("Fail reasons:")
            lines.append("")
            for r in reasons:
                lines.append(f"- {r}")
            lines.append("")
    lines.append("==========================================================")
    return "\n".join(lines)
