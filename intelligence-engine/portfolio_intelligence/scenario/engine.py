"""Scenario engine — portfolio impact under institutional shocks (no trading advice)."""

from __future__ import annotations

from typing import Any

# Sector shock betas (return impact approx)
SCENARIOS = {
    "interest_rate_shock": {"banks": -0.08, "it_services": -0.03, "fmcg": -0.02, "telecom": -0.05, "consumer_internet": -0.07, "energy_conglomerate": -0.04},
    "oil_shock": {"banks": -0.03, "it_services": -0.02, "fmcg": -0.04, "telecom": -0.02, "consumer_internet": -0.03, "energy_conglomerate": 0.06},
    "currency_shock": {"banks": -0.02, "it_services": 0.04, "fmcg": -0.03, "telecom": -0.02, "consumer_internet": -0.04, "energy_conglomerate": 0.01},
    "inflation_shock": {"banks": -0.04, "it_services": -0.02, "fmcg": 0.01, "telecom": -0.03, "consumer_internet": -0.05, "energy_conglomerate": 0.02},
    "recession": {"banks": -0.12, "it_services": -0.08, "fmcg": -0.04, "telecom": -0.06, "consumer_internet": -0.15, "energy_conglomerate": -0.07},
    "credit_event": {"banks": -0.15, "it_services": -0.04, "fmcg": -0.03, "telecom": -0.05, "consumer_internet": -0.08, "energy_conglomerate": -0.06},
    "sector_rotation": {"banks": 0.03, "it_services": -0.05, "fmcg": -0.02, "telecom": 0.02, "consumer_internet": -0.06, "energy_conglomerate": 0.04},
    "market_correction": {"banks": -0.10, "it_services": -0.09, "fmcg": -0.06, "telecom": -0.11, "consumer_internet": -0.16, "energy_conglomerate": -0.09},
}


def run_scenarios(holdings: list[dict[str, Any]], *, cash_weight: float) -> dict[str, Any]:
    results = []
    for name, shocks in SCENARIOS.items():
        impact = float(cash_weight or 0) * 0.0
        for h in holdings:
            w = float(h.get("weight") or 0)
            sector = str(h.get("sector") or "other")
            impact += w * float(shocks.get(sector, -0.05))
        results.append(
            {
                "scenario": name,
                "portfolio_impact_pct": round(impact * 100.0, 2),
                "severity": "severe" if impact <= -0.12 else "material" if impact <= -0.06 else "moderate",
            }
        )
    results.sort(key=lambda r: r["portfolio_impact_pct"])
    coverage = 100.0  # all 8 scenarios run
    return {
        "scenarios": results,
        "worst": results[0] if results else None,
        "scenario_coverage": coverage,
        "rule": "Scenario impacts are portfolio context — not trade instructions",
    }
