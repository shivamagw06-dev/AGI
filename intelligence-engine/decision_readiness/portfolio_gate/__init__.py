"""Portfolio and capital-allocation readiness gate."""

from __future__ import annotations

from typing import Any


def evaluate_portfolio(
    thesis: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    context = payload.get("portfolio_context")
    context = context if isinstance(context, dict) else {}
    pillars = {
        p.get("pillar"): p for p in (thesis.get("supporting_pillars") or [])
    }
    portfolio_strength = float(
        (pillars.get("Portfolio Fit") or {}).get("strength") or 0.5
    )
    valuation_strength = float(
        (pillars.get("Valuation") or {}).get("strength") or 0.5
    )
    suitability = float(context.get("position_suitability", portfolio_strength))
    sector_concentration = float(context.get("sector_concentration", 0.22))
    factor_exposure = float(context.get("factor_exposure", 0.28))
    risk_budget_used = float(context.get("risk_budget_used", 0.72))
    liquidity = float(context.get("liquidity", 0.9))
    diversification = float(context.get("diversification", 0.7))

    concentration_score = max(0.0, min(1.0, 1.0 - sector_concentration / 0.5))
    factor_score = max(0.0, min(1.0, 1.0 - factor_exposure / 0.65))
    risk_score = max(0.0, min(1.0, 1.0 - max(0.0, risk_budget_used - 0.65) / 0.35))
    score = (
        0.25 * suitability
        + 0.15 * concentration_score
        + 0.15 * factor_score
        + 0.15 * risk_score
        + 0.15 * liquidity
        + 0.15 * diversification
    )
    score = max(0.0, min(1.0, score))

    # Capital allocation readiness explicitly differs from thesis quality.
    capital = (
        0.30 * suitability
        + 0.22 * valuation_strength
        + 0.16 * concentration_score
        + 0.14 * risk_score
        + 0.10 * liquidity
        + 0.08 * diversification
    )
    capital = max(0.0, min(1.0, capital))
    constraints = []
    if sector_concentration > 0.30:
        constraints.append("Sector concentration exceeds 30%")
    if factor_exposure > 0.45:
        constraints.append("Factor exposure is elevated")
    if risk_budget_used > 0.85:
        constraints.append("Risk budget nearly exhausted")
    if liquidity < 0.65:
        constraints.append("Liquidity below institutional threshold")
    if valuation_strength < 0.5:
        constraints.append("Valuation does not support incremental capital")

    return {
        "dimension": "Portfolio",
        "score": round(score, 4),
        "score_pct": round(score * 100),
        "passed": score >= 0.7 and not any(
            "exceeds" in c or "exhausted" in c or "below" in c
            for c in constraints
        ),
        "checks": {
            "position_suitability": round(suitability, 4),
            "sector_concentration": round(sector_concentration, 4),
            "factor_exposure": round(factor_exposure, 4),
            "risk_budget_used": round(risk_budget_used, 4),
            "liquidity": round(liquidity, 4),
            "diversification": round(diversification, 4),
        },
        "constraints": constraints,
        "capital_allocation_readiness": round(capital, 4),
        "capital_allocation_readiness_pct": round(capital * 100),
        "capital_state": (
            "READY"
            if capital >= 0.8
            else "READY WITH LIMITS"
            if capital >= 0.65
            else "DO NOT ADD CAPITAL"
        ),
        "separate_from_thesis_quality": True,
    }
