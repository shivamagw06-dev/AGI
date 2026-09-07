"""Deterministic multi-dimension similarity scoring for sector analogues."""

from __future__ import annotations

from typing import Any

from historical_sector_analogue_intelligence.schema import (
    ConfidenceLabel,
    DimensionScore,
    SIMILARITY_DIMENSIONS,
)

# Weights must sum to 1.0
DIMENSION_WEIGHTS: dict[str, float] = {
    "revenue_growth": 0.12,
    "earnings_growth": 0.10,
    "margin_profile": 0.10,
    "roe": 0.10,
    "valuation": 0.12,
    "relative_performance": 0.08,
    "interest_rate": 0.10,
    "inflation": 0.08,
    "currency": 0.06,
    "policy": 0.08,
    "industry_structure": 0.06,
}

# Absolute distance that maps to ~0 similarity for each dimension.
DIMENSION_SCALES: dict[str, float] = {
    "revenue_growth": 15.0,  # pp yoy
    "earnings_growth": 25.0,  # pp yoy
    "margin_profile": 6.0,  # pp EBITDA margin
    "roe": 8.0,  # pp ROE
    "valuation": 12.0,  # PE turns
    "relative_performance": 20.0,  # relative return pp
    "interest_rate": 3.0,  # pp repo
    "inflation": 4.0,  # pp CPI
    "currency": 8.0,  # USDINR points
    "policy": 3.0,  # policy support index 0-10
    "industry_structure": 3.0,  # concentration / util index 0-10
}

DIMENSION_LABELS: dict[str, str] = {
    "revenue_growth": "Revenue Growth",
    "earnings_growth": "Earnings Growth",
    "margin_profile": "Margin Profile",
    "roe": "ROE",
    "valuation": "Valuation",
    "relative_performance": "Relative Performance",
    "interest_rate": "Interest-Rate Environment",
    "inflation": "Inflation Environment",
    "currency": "Currency Environment",
    "policy": "Policy Environment",
    "industry_structure": "Industry Structure",
}

MATCH_THRESHOLD = 70.0


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def relative_similarity(current: float | None, historical: float | None, *, scale: float) -> float:
    """Score 0-100 from relative distance. `scale` maps to ~0 score."""
    if current is None or historical is None:
        return 0.0
    if scale <= 0:
        return 100.0 if current == historical else 0.0
    dist = abs(float(current) - float(historical))
    return _clamp(100.0 * (1.0 - dist / scale))


def score_dimensions(
    current: dict[str, float],
    historical: dict[str, float],
    *,
    weights: dict[str, float] | None = None,
    scales: dict[str, float] | None = None,
) -> tuple[float, list[DimensionScore], list[str], list[str]]:
    """Weighted similarity. Returns overall, detail, matching, non-matching."""
    weights = weights or DIMENSION_WEIGHTS
    scales = scales or DIMENSION_SCALES
    details: list[DimensionScore] = []
    matching: list[str] = []
    non_matching: list[str] = []
    total_w = 0.0
    acc = 0.0

    for dim in SIMILARITY_DIMENSIONS:
        weight = float(weights.get(dim, 0.0))
        if weight <= 0:
            continue
        cur = current.get(dim)
        hist = historical.get(dim)
        if cur is None or hist is None:
            details.append(
                DimensionScore(
                    dimension=DIMENSION_LABELS.get(dim, dim),
                    dimension_key=dim,
                    current_value=cur,
                    historical_value=hist,
                    score=0.0,
                    weight=weight,
                    matched=False,
                    scale=float(scales.get(dim, 1.0)),
                )
            )
            non_matching.append(DIMENSION_LABELS.get(dim, dim))
            continue
        scale = float(scales.get(dim, 1.0))
        dim_score = relative_similarity(cur, hist, scale=scale)
        matched = dim_score >= MATCH_THRESHOLD
        label = DIMENSION_LABELS.get(dim, dim)
        details.append(
            DimensionScore(
                dimension=label,
                dimension_key=dim,
                current_value=float(cur),
                historical_value=float(hist),
                score=round(dim_score, 2),
                weight=weight,
                matched=matched,
                scale=scale,
            )
        )
        if matched:
            matching.append(label)
        else:
            non_matching.append(label)
        acc += dim_score * weight
        total_w += weight

    overall = round(acc / total_w, 2) if total_w else 0.0
    return overall, details, matching, non_matching


def confidence_for(score: float, *, evidence_n: int, dimensions_scored: int) -> ConfidenceLabel:
    if score >= 85 and evidence_n >= 2 and dimensions_scored >= 6:
        return "High"
    if score >= 70 and evidence_n >= 1:
        return "Medium"
    if score >= 55:
        return "Medium"
    return "Low"


def key_differences(details: list[DimensionScore], *, max_n: int = 4) -> list[str]:
    gaps: list[tuple[float, str]] = []
    for d in details:
        if d.current_value is None or d.historical_value is None:
            gaps.append((999.0, f"{d.dimension}: missing historical or current observation"))
            continue
        if d.matched:
            continue
        gap = abs(float(d.current_value) - float(d.historical_value))
        gaps.append(
            (
                gap,
                f"{d.dimension}: current {d.current_value} vs historical {d.historical_value} "
                f"(score {d.score})",
            )
        )
    gaps.sort(key=lambda x: x[0], reverse=True)
    return [g[1] for g in gaps[:max_n]]


def explainability_bundle(
    overall: float,
    details: list[DimensionScore],
    *,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    weights = weights or DIMENSION_WEIGHTS
    return {
        "method": "weighted_relative_distance",
        "formula": "sum(dim_score_i * weight_i) / sum(weights_present)",
        "overall_similarity": overall,
        "match_threshold": MATCH_THRESHOLD,
        "weights": dict(weights),
        "dimensions_scored": sum(
            1 for d in details if d.current_value is not None and d.historical_value is not None
        ),
        "dimension_contributions": [
            {
                "dimension": d.dimension_key,
                "score": d.score,
                "weight": d.weight,
                "contribution": round(d.score * d.weight, 2)
                if d.current_value is not None and d.historical_value is not None
                else 0.0,
                "matched": d.matched,
            }
            for d in details
        ],
        "deterministic": True,
    }
