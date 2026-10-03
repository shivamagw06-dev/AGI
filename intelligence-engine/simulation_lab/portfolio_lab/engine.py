"""Portfolio lab — expected behaviour under proposed weight / sleeve changes."""

from __future__ import annotations

from typing import Any


def simulate_portfolio_change(
    *,
    ticker: str,
    portfolio_id: str,
    assumptions: dict[str, Any],
    distribution: dict[str, Any],
) -> dict[str, Any]:
    delta = float(assumptions.get("weight_delta_bps") or 0)
    abs_delta = abs(delta) / 10000.0
    bands = distribution.get("bands") or {}
    quality_delta = round(0.4 if delta > 0 else (-0.3 if delta < 0 else 0.0), 2)
    # Directional institutional metrics — not buy/sell advice
    return {
        "portfolio_id": portfolio_id,
        "ticker": ticker,
        "weight_delta_bps": delta,
        "expected_return": distribution.get("expected_return"),
        "expected_volatility": distribution.get("expected_volatility"),
        "maximum_drawdown": distribution.get("max_drawdown_proxy"),
        "liquidity": "adequate" if abs_delta < 0.03 else "watch",
        "sector_exposure_delta": {
            "banks" if ticker == "HDFCBANK" else "it" if ticker == "TCS" else "staples": round(delta, 1)
        },
        "factor_exposure_delta": {
            "quality": round(quality_delta * (1 if delta >= 0 else -1), 2),
            "value": round(-0.2 if delta > 0 else 0.2, 2),
            "growth": round(0.15 if ticker == "TCS" and delta > 0 else 0.05, 2),
        },
        "country_exposure": {"IN": "unchanged_core"},
        "quality_score_delta": quality_delta if delta > 0 else -abs(quality_delta),
        "business_quality": "franchise_supportive" if ticker in {"HDFCBANK", "NESTLEIND", "TCS"} else "review",
        "financial_quality": "aci_soft_slice",
        "management_quality": "mii_soft_slice",
        "accounting_quality": "aci_soft_slice",
        "bands": bands,
        "rule": "Portfolio lab measures change in quality, risk and exposure — not a trade ticket",
    }
