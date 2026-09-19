"""Framework 1 — Business Model Assessment."""

from __future__ import annotations

from typing import Any

from institutional_analysts.business.brain._text import as_list, blob_of, txt


def assess(evidence: dict[str, Any]) -> dict[str, Any]:
    name = evidence.get("company") or "the company"
    model = txt(evidence.get("business_model"))
    drivers = as_list(evidence.get("revenue_drivers"), limit=5)
    advantages = as_list(evidence.get("advantages"), limit=5)
    capital = txt(evidence.get("capital_allocation"))
    b = blob_of(model, drivers, advantages, capital)

    platform = "platform" if any(k in b for k in ("platform", "network", "ecosystem")) else "product / franchise"
    asset = (
        "asset-light"
        if any(k in b for k in ("fee", "franchise", "distribution", "software"))
        else "asset-intensive" if any(k in b for k in ("capex", "manufactur", "plant")) else "mixed capital intensity"
    )
    recurring = (
        "High recurring / relationship revenue character"
        if any(k in b for k in ("deposit", "subscription", "recurring", "fee", "franchise", "retention"))
        else "Mix of recurring and transactional revenue"
    )
    operating_leverage = (
        "Operating leverage available as scale compounds fixed franchise costs"
        if any(k in b for k in ("scale", "distribution", "network", "operating leverage"))
        else "Operating leverage depends on volume growth versus cost inflation"
    )
    cash = (
        "Cash generation is a core economic feature when underwriting and funding remain disciplined"
        if any(k in b for k in ("cash", "deposit", "fee", "franchise"))
        else "Cash conversion must be confirmed through the cycle"
    )

    why_value = (
        f"{name}'s economic engine creates value when revenue streams compound through "
        f"{', '.join(drivers[:2]) or 'core demand'} while cost and capital intensity remain controlled."
    )

    return {
        "framework": "Business Model",
        "completed": bool(model or drivers),
        "how_it_makes_money": model or f"{name} monetises its core franchise relationships.",
        "revenue_streams": drivers or ["Core franchise demand"],
        "profit_drivers": advantages[:3] or ["Scale efficiencies", "Mix", "Pricing discipline"],
        "cost_drivers": [
            "Customer acquisition / distribution cost",
            "Operating and compliance cost base",
            "Cost of growth capital",
        ],
        "recurring_vs_one_time": recurring,
        "platform_vs_product": platform,
        "asset_intensity": asset,
        "operating_leverage": operating_leverage,
        "cash_generation": cash,
        "assessment": why_value,
        "why_it_creates_value": why_value,
    }
