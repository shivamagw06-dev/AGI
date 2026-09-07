"""Optimisation engine — risk-adjusted quality, not return maximisation."""

from __future__ import annotations

from typing import Any


def optimisation_score(
    *,
    diversification: float,
    concentration: float,
    factor_balance: float,
    risk_score: float,
    portfolio_quality: float,
    liquidity: float,
) -> dict[str, Any]:
    # Never optimise for returns alone
    score = (
        diversification * 0.20
        + concentration * 0.15
        + factor_balance * 0.15
        + risk_score * 0.20
        + portfolio_quality * 0.20
        + liquidity * 0.10
    )
    return {
        "optimisation_score": round(score, 1),
        "objective": "risk_adjusted_quality_and_resilience",
        "never_returns_alone": True,
        "components": {
            "diversification": diversification,
            "concentration": concentration,
            "factor_balance": factor_balance,
            "risk": risk_score,
            "portfolio_quality": portfolio_quality,
            "liquidity": liquidity,
        },
        "note": "Improving this score means higher quality / better balance — not higher expected return",
    }
