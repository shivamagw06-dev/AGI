"""Deterministic framework-selection confidence."""

from __future__ import annotations

from typing import Any


def score_confidence(
    *,
    selected: list[dict[str, Any]],
    sector: str | None,
    sector_source: str,
    intent_v2: str | None,
    evidence_domains: list[str] | None,
    gaps_coverage: float | None,
    as_of: str | None,
    forbidden_rejected: list[str],
) -> dict[str, Any]:
    score = 0.35
    reasons: list[str] = []

    if sector and sector != "generic":
        score += 0.25
        reasons.append(f"sector_match:{sector}")
    elif sector_source == "keyword":
        score += 0.15
        reasons.append("sector_keyword")
    else:
        reasons.append("sector_weak")

    if intent_v2 and intent_v2 != "Unknown":
        score += 0.12
        reasons.append(f"intent:{intent_v2}")

    cov = float(gaps_coverage) if gaps_coverage is not None else 0.5
    score += 0.15 * max(0.0, min(1.0, cov))
    reasons.append(f"evidence_coverage:{round(cov, 3)}")

    n = len(selected)
    if n >= 2:
        score += 0.08
        reasons.append("multi_framework")
    elif n == 1:
        score += 0.03
        reasons.append("single_framework")
    else:
        score -= 0.2
        reasons.append("missing_framework")

    if forbidden_rejected:
        score += 0.05
        reasons.append("forbidden_excluded")

    if as_of:
        score += 0.03
        reasons.append("historical_compat_checked")

    # Primary present
    if any(r.get("role") == "primary" for r in selected):
        score += 0.05
        reasons.append("primary_present")

    score = max(0.0, min(0.99, score))
    band = (
        "High"
        if score >= 0.85
        else "Moderate"
        if score >= 0.65
        else "Low"
        if score >= 0.40
        else "Insufficient"
    )
    return {
        "score": round(score, 4),
        "band": band,
        "pct": int(round(score * 100)),
        "reasons": reasons,
        "fabricated": False,
    }
