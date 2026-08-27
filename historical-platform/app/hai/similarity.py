"""Deterministic multi-dimension similarity scoring for historical analogues."""

from __future__ import annotations

from typing import Any

from app.contracts.models import AnalogueConfidence, AnalogueDimensionScore


# Weights for company financial analogues (must sum ~1.0)
COMPANY_WEIGHTS: dict[str, float] = {
    "revenue_growth": 0.35,
    "pat_margin": 0.25,
    "pe": 0.25,
    "sector_alignment": 0.15,
}

SECTOR_WEIGHTS: dict[str, float] = {
    "demand_stress": 0.40,
    "fx_sensitivity": 0.20,
    "margin_pressure": 0.25,
    "cycle_phase": 0.15,
}

MACRO_WEIGHTS: dict[str, float] = {
    "policy_stance": 0.40,
    "inflation_direction": 0.30,
    "growth_direction": 0.30,
}

MARKET_WEIGHTS: dict[str, float] = {
    "valuation_regime": 0.35,
    "volatility": 0.25,
    "liquidity": 0.25,
    "risk_appetite": 0.15,
}


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def relative_similarity(current: float | None, historical: float | None, *, scale: float) -> float:
    """Score 0-100 from relative distance. `scale` is the distance that maps to ~0 score."""
    if current is None or historical is None:
        return 0.0
    if scale <= 0:
        return 100.0 if current == historical else 0.0
    dist = abs(float(current) - float(historical))
    return _clamp(100.0 * (1.0 - dist / scale))


def score_dimensions(
    current: dict[str, float],
    historical: dict[str, float],
    weights: dict[str, float],
    *,
    scales: dict[str, float] | None = None,
) -> tuple[float, list[AnalogueDimensionScore], list[str], list[str]]:
    """Weighted similarity across dimensions. Returns score, detail, matching, non-matching."""
    scales = scales or {}
    details: list[AnalogueDimensionScore] = []
    matching: list[str] = []
    non_matching: list[str] = []
    total_w = 0.0
    acc = 0.0
    for dim, weight in weights.items():
        cur = current.get(dim)
        hist = historical.get(dim)
        scale = float(scales.get(dim, _default_scale(dim)))
        dim_score = relative_similarity(cur, hist, scale=scale)
        matched = dim_score >= 70.0
        label = _pretty(dim)
        details.append(
            AnalogueDimensionScore(
                dimension=label,
                current_value=cur,
                historical_value=hist,
                score=round(dim_score, 2),
                matched=matched,
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


def confidence_for(score: float, *, evidence_n: int) -> AnalogueConfidence:
    if score >= 85 and evidence_n >= 2:
        return AnalogueConfidence.HIGH
    if score >= 70 and evidence_n >= 1:
        return AnalogueConfidence.MEDIUM
    if score >= 55:
        return AnalogueConfidence.MEDIUM
    return AnalogueConfidence.LOW


def _default_scale(dim: str) -> float:
    return {
        "revenue_growth": 12.0,  # pp
        "pat_margin": 0.08,
        "pe": 8.0,
        "sector_alignment": 1.0,
        "demand_stress": 1.0,
        "fx_sensitivity": 1.0,
        "margin_pressure": 1.0,
        "cycle_phase": 1.0,
        "policy_stance": 1.0,
        "inflation_direction": 1.0,
        "growth_direction": 1.0,
        "valuation_regime": 1.0,
        "volatility": 1.0,
        "liquidity": 1.0,
        "risk_appetite": 1.0,
    }.get(dim, 1.0)


def _pretty(dim: str) -> str:
    return {
        "revenue_growth": "Revenue Growth",
        "pat_margin": "Margins",
        "pe": "Valuation",
        "sector_alignment": "Sector",
        "demand_stress": "Demand Stress",
        "fx_sensitivity": "FX Sensitivity",
        "margin_pressure": "Margin Pressure",
        "cycle_phase": "Cycle Phase",
        "policy_stance": "Policy Stance",
        "inflation_direction": "Inflation",
        "growth_direction": "GDP Growth",
        "valuation_regime": "Valuation Regime",
        "volatility": "Volatility",
        "liquidity": "Liquidity",
        "risk_appetite": "Risk Appetite",
    }.get(dim, dim.replace("_", " ").title())


def outcome_from_next(
    periods: list[dict[str, Any]],
    index: int,
    *,
    growth_key: str = "revenue_growth",
) -> str | None:
    """Describe what happened after the matched period when next period exists."""
    if index < 0 or index >= len(periods) - 1:
        return None
    nxt = periods[index + 1]
    cur = periods[index]
    g0 = cur.get(growth_key)
    g1 = nxt.get(growth_key)
    label = nxt.get("period") or nxt.get("matched_period")
    if g0 is None or g1 is None:
        return f"Subsequent period {label} available in historical store"
    if float(g1) > float(g0) + 1.0:
        return f"Growth recovered into {label} ({g0}% → {g1}%)"
    if float(g1) < float(g0) - 1.0:
        return f"Slowdown deepened into {label} ({g0}% → {g1}%)"
    return f"Conditions persisted into {label} (growth ~{g1}%)"
