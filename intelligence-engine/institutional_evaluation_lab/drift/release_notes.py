"""Auto-generated release notes from drift analysis."""

from __future__ import annotations

from typing import Any


def _sector_buckets(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        sec = str(r.get("sector") or "Unknown")
        out.setdefault(sec, []).append(r)
    return out


def _sector_score(items: list[dict[str, Any]]) -> float:
    """Positive = improvement (readiness up / unknown down); negative = regression."""
    if not items:
        return 0.0
    score = 0.0
    for r in items:
        code = str((r.get("reason") or {}).get("code") or "")
        mag = r.get("magnitude") or {}
        ready = (mag.get("by_field") or {}).get("recommendation_readiness") or {}
        delta = ready.get("delta")
        if delta is not None:
            score += float(delta)
        if code == "UNKNOWN":
            score -= 5
        if code == "DATA" and r.get("decision_changed"):
            score += 1
    return score


def build_release_notes(report: dict[str, Any]) -> dict[str, Any]:
    rows = report.get("rows") or []
    changed = [r for r in rows if r.get("decision_changed")]
    expected = [
        r
        for r in changed
        if str((r.get("reason") or {}).get("code")) in {"DATA", "MARKET", "MODEL", "GOVERNANCE", "BUGFIX"}
    ]
    unexpected = [r for r in changed if str((r.get("reason") or {}).get("code")) == "UNKNOWN"]

    by_sector = _sector_buckets(rows)
    sector_scores = {s: _sector_score(items) for s, items in by_sector.items()}
    largest_improvement = max(sector_scores, key=sector_scores.get) if sector_scores else None
    largest_regression = min(sector_scores, key=sector_scores.get) if sector_scores else None

    cov = report.get("coverage") or {}
    health = report.get("health") or {}
    budget = report.get("budget") or {}
    review = report.get("review_queue") or {}

    notes = {
        "title": f"Release {report.get('current_release')}",
        "previous_release": report.get("previous_release"),
        "current_release": report.get("current_release"),
        "companies_evaluated": report.get("n"),
        "recommendations_changed": len(changed),
        "expected": len(expected),
        "unexpected": len(unexpected),
        "governance_violations": int(
            (budget.get("observed") or {}).get("governance_failures")
            if budget.get("observed") is not None
            else report.get("governance_failures")
            or 0
        ),
        "average_runtime_s": (
            round((health.get("average_runtime_ms") or cov.get("average_runtime_ms") or 0) / 1000.0, 2)
            if (health.get("average_runtime_ms") or cov.get("average_runtime_ms"))
            else None
        ),
        "coverage_pct": cov.get("gate_pass_rate_pct")
        or (
            round(100.0 * float(health.get("gate_pass_rate")), 1)
            if health.get("gate_pass_rate") is not None
            else None
        ),
        "largest_improvement": largest_improvement,
        "largest_regression": largest_regression
        if largest_regression != largest_improvement
        else None,
        "budget_passed": budget.get("passed"),
        "requires_review": review.get("requires_review"),
        "by_reason_code": report.get("by_reason_code"),
    }
    return notes


def format_release_notes(notes: dict[str, Any]) -> str:
    lines = [
        f"Release {notes.get('current_release')}",
        "",
        f"{notes.get('companies_evaluated')} companies evaluated",
        "",
        "Recommendations changed",
        "",
        str(notes.get("recommendations_changed")),
        "",
        "Expected",
        "",
        str(notes.get("expected")),
        "",
        "Unexpected",
        "",
        str(notes.get("unexpected")),
        "",
        "Governance violations",
        "",
        str(notes.get("governance_violations")),
        "",
        "Average runtime",
        "",
        f"{notes.get('average_runtime_s')} s" if notes.get("average_runtime_s") is not None else "n/a",
        "",
        "Coverage",
        "",
        f"{notes.get('coverage_pct')}%" if notes.get("coverage_pct") is not None else "n/a",
        "",
        "Largest improvement",
        "",
        str(notes.get("largest_improvement") or "n/a"),
        "",
        "Largest regression",
        "",
        str(notes.get("largest_regression") or "n/a"),
    ]
    return "\n".join(lines)
