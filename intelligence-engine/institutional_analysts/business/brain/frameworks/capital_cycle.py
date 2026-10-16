"""Framework 5 — Capital Cycle."""

from __future__ import annotations

from typing import Any

from institutional_analysts.business.brain._text import as_list, blob_of, txt


def assess(evidence: dict[str, Any]) -> dict[str, Any]:
    name = evidence.get("company") or "the company"
    growth = as_list(evidence.get("growth_opportunities"), limit=4)
    risks = as_list(evidence.get("business_risks"), limit=5)
    capital = txt(evidence.get("capital_allocation"))
    b = blob_of(growth, risks, capital, evidence.get("business_model"))

    capacity = (
        "Industry capacity expanding — watch return dilution"
        if any(k in b for k in ("capacity", "new entrant", "aggressive", "overbuild"))
        else "Capacity growth appears measured relative to demand"
    )
    demand = (
        "Structural demand growth supports reinvestment"
        if growth or any(k in b for k in ("share gain", "credit growth", "market expansion"))
        else "Demand growth not yet clearly above industry supply growth"
    )
    intensity = (
        "Capital intensive — incremental returns depend on underwriting / project discipline"
        if any(k in b for k in ("capex", "capital intensive", "balance sheet", "credit"))
        else "Moderate capital intensity with room for compounding reinvestment"
    )
    expected = (
        f"For {name}, expected returns on incremental capital remain attractive when growth is funded "
        "without permanently sacrificing underwriting or funding discipline."
        if "dilution" not in capacity.lower()
        else f"For {name}, incremental industry capital risks compressing returns unless differentiation holds."
    )

    return {
        "framework": "Capital Cycle",
        "completed": True,
        "industry_investment": capacity,
        "capacity": capacity,
        "supply_growth": capacity,
        "demand_growth": demand,
        "capital_intensity": intensity,
        "expected_returns": expected,
        "assessment": expected,
    }
