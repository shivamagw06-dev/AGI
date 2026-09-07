"""Sensitivity engine — rates, inflation, oil, FX, GDP, yields, credit, commodities, regulation, demand."""

from __future__ import annotations

from typing import Any

FACTORS = (
    "interest_rates",
    "inflation",
    "oil",
    "currencies",
    "gdp",
    "bond_yields",
    "credit_growth",
    "commodity_prices",
    "regulation",
    "consumer_demand",
)


def sensitivity_matrix(profile: dict[str, Any]) -> dict[str, Any]:
    weights = profile.get("sensitivity_weights") or {}
    rows = []
    for f in FACTORS:
        w = float(weights.get(f) or 0.3)
        rows.append(
            {
                "factor": f,
                "sensitivity": round(w, 3),
                "band": "high" if w >= 0.7 else "moderate" if w >= 0.4 else "low",
                "evidence": {
                    "source": "forecast_intelligence.sensitivity",
                    "note": f"Sector/company prior sensitivity to {f}",
                },
            }
        )
    rows.sort(key=lambda r: -r["sensitivity"])
    heatmap = {r["factor"]: r["sensitivity"] for r in rows}
    return {
        "factors": rows,
        "heatmap": heatmap,
        "top_sensitivities": rows[:5],
        "rule": "Sensitivity is factor exposure of scenarios — not a price forecast",
    }
