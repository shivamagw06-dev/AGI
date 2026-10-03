"""Position impact — does the candidate improve this portfolio?"""

from __future__ import annotations

from typing import Any


def position_impact(
    *,
    current: dict[str, Any],
    pro_forma: dict[str, Any],
    overlap: dict[str, Any],
) -> dict[str, Any]:
    def g(block: dict[str, Any], *keys: str, default: float = 0.0) -> float:
        cur: Any = block
        for k in keys:
            if not isinstance(cur, dict):
                return default
            cur = cur.get(k)
        try:
            return float(cur)
        except Exception:
            return default

    div_delta = g(pro_forma, "diversification", "diversification") - g(current, "diversification", "diversification")
    conc_delta = g(pro_forma, "concentration", "concentration") - g(current, "concentration", "concentration")
    risk_delta = g(current, "risk", "expected_volatility") - g(pro_forma, "risk", "expected_volatility")
    # positive risk_delta => risk falls (good)
    qual_delta = g(pro_forma, "portfolio_quality", "portfolio_quality") - g(
        current, "portfolio_quality", "portfolio_quality"
    )
    liq_delta = g(pro_forma, "liquidity", "liquidity") - g(current, "liquidity", "liquidity")

    improves_div = div_delta > 0.5
    increases_conc = conc_delta < -0.5  # concentration score down = worse
    improves_quality = qual_delta > 0.3
    raises_risk = risk_delta < -0.005  # vol up
    liq_worse = liq_delta < -1.0

    sector_breach = bool((pro_forma.get("allocation") or {}).get("sector_limit_breaches"))

    return {
        "diversification_improves": improves_div,
        "diversification_delta": round(div_delta, 2),
        "concentration_increases": increases_conc,
        "concentration_delta": round(conc_delta, 2),
        "expected_quality_improves": improves_quality,
        "quality_delta": round(qual_delta, 2),
        "portfolio_risk_rises": raises_risk,
        "risk_vol_delta": round(-risk_delta, 4),
        "liquidity_deteriorates": liq_worse,
        "liquidity_delta": round(liq_delta, 2),
        "sector_concentration_exceeds_limits": sector_breach,
        "overlap": overlap,
        "net_portfolio_effect": (
            "improves"
            if improves_div and improves_quality and not raises_risk and not sector_breach
            else "mixed"
            if improves_quality or improves_div
            else "weakens"
        ),
    }
