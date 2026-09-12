"""Section and dossier confidence from coverage / freshness / depth."""

from __future__ import annotations

from typing import Any


def level_from_score(score: float) -> str:
    if score >= 0.75:
        return "High"
    if score >= 0.45:
        return "Medium"
    return "Low"


def section_confidence(
    *,
    required_hits: int,
    required_total: int,
    observations: int = 0,
    missing: list[str] | None = None,
) -> dict[str, Any]:
    base = (required_hits / required_total) if required_total else 0.0
    depth = min(1.0, observations / 24.0) if observations else 0.0
    miss_penalty = min(0.35, 0.08 * len(missing or []))
    score = max(0.0, min(1.0, 0.7 * base + 0.3 * depth - miss_penalty))
    return {
        "confidence": level_from_score(score),
        "score": round(score, 3),
        "required_hits": required_hits,
        "required_total": required_total,
        "observations": observations,
        "missing": list(missing or []),
    }


def dossier_quality(section_confidences: dict[str, dict[str, Any]], inputs: dict[str, bool]) -> dict[str, Any]:
    scores = [float(v.get("score") or 0) for v in section_confidences.values()]
    avg = sum(scores) / len(scores) if scores else 0.0
    coverage_pct = 100.0 * sum(1 for v in inputs.values() if v) / max(len(inputs), 1)
    high = sum(1 for v in section_confidences.values() if v.get("confidence") == "High")
    med = sum(1 for v in section_confidences.values() if v.get("confidence") == "Medium")
    low = sum(1 for v in section_confidences.values() if v.get("confidence") == "Low")
    return {
        "research_confidence": level_from_score(avg),
        "score": round(avg, 3),
        "business_understanding": level_from_score(
            float((section_confidences.get("business") or {}).get("score") or 0)
        ),
        "financial_quality": level_from_score(
            float((section_confidences.get("financial_quality") or {}).get("score") or 0)
        ),
        "historical_confidence": level_from_score(
            float((section_confidences.get("valuation") or {}).get("score") or 0)
        ),
        "valuation_confidence": level_from_score(
            float((section_confidences.get("valuation") or {}).get("score") or 0)
        ),
        "coverage_pct": round(coverage_pct, 1),
        "data_quality": level_from_score(coverage_pct / 100.0),
        "distribution": {"High": high, "Medium": med, "Low": low},
        "investment_rating": None,
        "recommendation": None,
    }
