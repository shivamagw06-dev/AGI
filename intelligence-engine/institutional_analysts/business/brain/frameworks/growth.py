"""Framework 10 — Long-term Growth Runway."""

from __future__ import annotations

from typing import Any

from institutional_analysts.business.brain._text import as_list, blob_of, txt


def assess(evidence: dict[str, Any]) -> dict[str, Any]:
    name = evidence.get("company") or "the company"
    growth = as_list(evidence.get("growth_opportunities"), limit=5)
    drivers = as_list(evidence.get("revenue_drivers"), limit=5)
    advantages = as_list(evidence.get("advantages"), limit=4)
    b = blob_of(growth, drivers, advantages, evidence.get("business_model"))

    structural = (
        "Structural demand and formalisation trends can extend the runway"
        if any(k in b for k in ("credit growth", "formal", "digital", "market expansion", "share"))
        or growth
        else "Structural runway not yet clearly differentiated from cyclical demand"
    )
    expansion = growth[:3] or drivers[:2] or ["Core market deepening"]
    international = (
        "International expansion is a secondary optionality, not the core thesis"
        if "international" in b
        else "Growth thesis is primarily domestic / core-market compounding"
    )
    technology = (
        "Technology widens distribution and lowers marginal cost to serve"
        if any(k in b for k in ("digital", "tech", "platform", "data"))
        else "Technology is an enabler; franchise economics remain the primary growth constraint"
    )

    runway = (
        f"{name} has a multi-year growth runway if {', '.join(expansion[:2]).lower()} "
        "can be funded without eroding underwriting or funding advantage."
        if expansion
        else f"{name}'s long-term growth runway remains incompletely evidenced."
    )

    return {
        "framework": "Long-term Growth",
        "completed": bool(growth or drivers),
        "growth_drivers": expansion,
        "structural_trends": structural,
        "market_expansion": expansion,
        "new_products": [g for g in growth if "product" in g.lower()] or ["Adjacent product deepening"],
        "international_expansion": international,
        "technology": technology,
        "runway": runway,
        "assessment": runway,
    }
