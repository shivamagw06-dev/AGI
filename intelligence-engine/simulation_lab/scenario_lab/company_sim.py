"""Company simulation helpers — revenue/margins/ROIC paths as assumption shifts."""

from __future__ import annotations

from typing import Any

from simulation_lab.schema import COMPANY_SIMULATIONS

IMPACT = {
    "revenue_growth": {"return_delta": 0.02, "vol_delta": 0.01},
    "margins": {"return_delta": 0.015, "vol_delta": 0.005},
    "roic": {"return_delta": 0.018, "vol_delta": 0.0},
    "cash_flow": {"return_delta": 0.012, "vol_delta": -0.005},
    "working_capital": {"return_delta": 0.008, "vol_delta": 0.004},
    "valuation_multiple": {"return_delta": 0.01, "vol_delta": 0.02},
    "capital_allocation": {"return_delta": 0.014, "vol_delta": 0.008},
    "management_change": {"return_delta": -0.01, "vol_delta": 0.03},
    "regulatory_shock": {"return_delta": -0.03, "vol_delta": 0.04},
    "acquisition": {"return_delta": 0.005, "vol_delta": 0.035},
}


def company_assumption_shift(assumptions: dict[str, Any]) -> dict[str, Any]:
    active = []
    rd = 0.0
    vd = 0.0
    for key in COMPANY_SIMULATIONS:
        if assumptions.get(key) or assumptions.get("company_simulation") == key:
            meta = IMPACT[key]
            active.append(key)
            rd += meta["return_delta"]
            vd += meta["vol_delta"]
    return {
        "active": active,
        "return_delta": round(rd, 4),
        "vol_delta": round(vd, 4),
        "available": list(COMPANY_SIMULATIONS),
    }
