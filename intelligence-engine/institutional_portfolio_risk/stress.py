"""PRE-01 stress engine — deterministic scenario shocks (no Monte Carlo)."""

from __future__ import annotations

from typing import Sequence

from institutional_portfolio.portfolio_entities import HoldingRecord
from institutional_portfolio_risk.models import StressResult
from institutional_portfolio_risk.schema import STRESS_SCENARIOS

# scenario → (label, sector_shock_map, default_shock)
# Shocks are approximate equity returns under the scenario.
_SCENARIO_DEFS: dict[str, tuple[str, dict[str, float], float]] = {
    "rbi_plus_50bps": (
        "RBI +50 bps",
        {
            "banking": -0.06,
            "banks": -0.06,
            "financials": -0.05,
            "technology": -0.02,
            "energy": -0.03,
        },
        -0.025,
    ),
    "rbi_minus_50bps": (
        "RBI -50 bps",
        {
            "banking": 0.05,
            "banks": 0.05,
            "financials": 0.045,
            "technology": 0.02,
            "energy": 0.015,
        },
        0.02,
    ),
    "market_minus_10": (
        "Market -10%",
        {},
        -0.10,
    ),
    "market_minus_20": (
        "Market -20%",
        {},
        -0.20,
    ),
    "oil_shock": (
        "Oil Shock",
        {
            "energy": 0.08,
            "oil & gas": 0.08,
            "banking": -0.04,
            "banks": -0.04,
            "financials": -0.035,
            "technology": -0.03,
            "auto": -0.07,
        },
        -0.03,
    ),
    "inr_shock": (
        "INR Shock",
        {
            "technology": 0.04,
            "information technology": 0.04,
            "it": 0.04,
            "energy": -0.03,
            "banking": -0.025,
            "banks": -0.025,
        },
        -0.02,
    ),
    "banking_stress": (
        "Banking Stress",
        {
            "banking": -0.18,
            "banks": -0.18,
            "financials": -0.15,
            "technology": -0.04,
            "energy": -0.05,
        },
        -0.04,
    ),
}


def _severity(impact: float) -> str:
    mag = abs(impact)
    if mag >= 0.15:
        return "critical"
    if mag >= 0.08:
        return "high"
    if mag >= 0.04:
        return "medium"
    return "low"


def evaluate_stress(
    holdings: Sequence[HoldingRecord],
    *,
    cash_weight: float = 0.0,
    scenarios: Sequence[str] | None = None,
) -> tuple[StressResult, ...]:
    wanted = list(scenarios) if scenarios else list(STRESS_SCENARIOS)
    results: list[StressResult] = []
    for key in wanted:
        if key not in _SCENARIO_DEFS:
            continue
        label, sector_map, default = _SCENARIO_DEFS[key]
        impact = 0.0
        affected: list[str] = []
        for h in holdings:
            w = float(h.weight or 0.0)
            sector = (h.sector or "").strip().lower()
            shock = sector_map.get(sector, default)
            # Market scenarios apply beta-ish default uniformly
            if key.startswith("market_"):
                shock = default
            impact += w * shock
            if abs(shock) >= 0.04:
                affected.append(h.ticker)
        # Cash dampens absolute equity impact
        impact *= max(0.0, 1.0 - float(cash_weight) * 0.5)
        results.append(
            StressResult(
                scenario=key,
                label=label,
                portfolio_impact_pct=round(impact * 100.0, 3),
                severity=_severity(impact),
                affected_holdings=tuple(affected),
                detail=f"Deterministic shock under {label}",
            )
        )
    return tuple(results)


def worst_stress(results: Sequence[StressResult]) -> StressResult | None:
    if not results:
        return None
    return min(results, key=lambda r: float(r.portfolio_impact_pct))
