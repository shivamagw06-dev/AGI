"""MIE confidence scoring — freshness, coverage, consistency."""

from __future__ import annotations

from typing import Any


def section_confidence(
    *,
    required_hits: int,
    required_total: int,
    observations: int = 0,
    missing: list[str] | None = None,
) -> dict[str, Any]:
    coverage = (required_hits / required_total) if required_total else 0.0
    obs_boost = min(0.25, observations / 40.0)
    score = min(0.95, 0.35 + 0.45 * coverage + obs_boost)
    if coverage >= 0.8 and observations >= 3:
        level = "High"
    elif coverage >= 0.45:
        level = "Medium"
    else:
        level = "Low"
    return {
        "confidence": level,
        "score": round(score, 3),
        "coverage": round(coverage * 100, 1),
        "observations": observations,
        "missing": list(missing or [])[:8],
    }


def pack_quality(confidences: dict[str, dict[str, Any]], inputs_present: dict[str, bool]) -> dict[str, Any]:
    scores = [float(c.get("score") or 0) for c in confidences.values() if c]
    avg = sum(scores) / len(scores) if scores else 0.0
    present = sum(1 for v in inputs_present.values() if v)
    total = max(len(inputs_present), 1)
    coverage_pct = round(100.0 * present / total, 1)
    if avg >= 0.72 and coverage_pct >= 70:
        level = "High"
    elif avg >= 0.45 and coverage_pct >= 40:
        level = "Medium"
    else:
        level = "Low"
    return {
        "macro_confidence": level,
        "score": round(avg, 3),
        "coverage_pct": coverage_pct,
        "inputs_present": present,
        "inputs_total": total,
        "recommendation": None,
        "investment_rating": None,
        "target_price": None,
    }
