"""Evidence readiness: coverage, authority, freshness, independence and contradictions."""

from __future__ import annotations

from typing import Any


def evaluate_evidence(
    thesis: dict[str, Any],
    debate: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    metrics = payload.get("evidence_metrics")
    metrics = metrics if isinstance(metrics, dict) else {}
    pillars = thesis.get("supporting_pillars") or []
    backed = sum(1 for p in pillars if p.get("evidence_backed", bool(p.get("evidence"))))
    inferred_coverage = backed / max(len(pillars), 1)
    coverage = float(metrics.get("coverage", inferred_coverage))
    if coverage > 1:
        coverage /= 100.0
    authority = float(metrics.get("authority", 0.9 if backed else 0.45))
    freshness = float(metrics.get("freshness", 0.88 if backed else 0.5))
    independence = float(metrics.get("independence", 0.84 if backed else 0.45))
    contradiction_coverage = float(
        metrics.get(
            "contradiction_coverage",
            min(1.0, len(debate.get("evidence_conflicts") or []) / 4.0),
        )
    )
    missing = list(
        dict.fromkeys(
            [str(x) for x in (thesis.get("missing_evidence") or [])]
            + [str(x) for x in (debate.get("required_evidence") or [])]
        )
    )
    critical_missing = [
        item for item in missing if any(
            token in item.lower()
            for token in ("critical", "independent", "risk", "valuation", "portfolio")
        )
    ]
    score = (
        0.35 * coverage
        + 0.17 * authority
        + 0.13 * freshness
        + 0.15 * independence
        + 0.20 * contradiction_coverage
    )
    score -= min(0.18, 0.015 * len(critical_missing))
    score = max(0.0, min(1.0, score))
    return {
        "dimension": "Evidence",
        "score": round(score, 4),
        "score_pct": round(score * 100),
        "passed": coverage >= 0.90 and not critical_missing,
        "checks": {
            "coverage": round(coverage, 4),
            "authority": round(authority, 4),
            "freshness": round(freshness, 4),
            "independence": round(independence, 4),
            "contradiction_coverage": round(contradiction_coverage, 4),
        },
        "coverage_pct": round(coverage * 100),
        "missing_critical_evidence": critical_missing[:10],
        "missing_evidence": missing[:15],
        "strengths": [
            label
            for label, value in {
                "High evidence coverage": coverage,
                "Authoritative sources": authority,
                "Fresh evidence": freshness,
                "Independent corroboration": independence,
                "Contradictions covered": contradiction_coverage,
            }.items()
            if value >= 0.85
        ],
        "weaknesses": [
            label
            for label, value in {
                "Evidence coverage below 90%": coverage,
                "Authority needs improvement": authority,
                "Evidence requires refresh": freshness,
                "Independence insufficient": independence,
                "Contradictions under-tested": contradiction_coverage,
            }.items()
            if value < 0.75
        ],
    }
