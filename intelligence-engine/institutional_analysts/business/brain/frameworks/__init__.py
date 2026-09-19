"""Business Analyst V2 — apply all institutional frameworks to assembled evidence."""

from __future__ import annotations

from typing import Any

from institutional_analysts.business.brain.frameworks import (
    business_model,
    capital_allocation,
    capital_cycle,
    competitive_advantage,
    customer_economics,
    growth,
    management,
    porter,
    pricing_power,
    risks,
    value_chain,
)


def apply_all(evidence: dict[str, Any]) -> dict[str, Any]:
    bm = business_model.assess(evidence)
    moat = competitive_advantage.assess(evidence)
    five = porter.assess(evidence)
    chain = value_chain.assess(evidence)
    cycle = capital_cycle.assess(evidence)
    customers = customer_economics.assess(evidence)
    pricing = pricing_power.assess(evidence)
    mgmt = management.assess(evidence)
    capital = capital_allocation.assess(evidence)
    runway = growth.assess(evidence)
    biz_risks = risks.assess(evidence)

    applied = [
        bm["framework"],
        moat["framework"],
        five["framework"],
        chain["framework"],
        cycle["framework"],
        customers["framework"],
        pricing["framework"],
        mgmt["framework"],
        capital["framework"],
        runway["framework"],
        biz_risks["framework"],
        "Quality Score",
    ]

    # V1-compatible aliases used by older callers / tests
    return {
        "applied": applied,
        "business_model": bm,
        "competitive_advantage": moat,
        "moat": moat,
        "porter_five_forces": five,
        "value_chain": chain,
        "value_creation": {
            "framework": "Value Chain / How it makes money",
            "business_model": bm.get("how_it_makes_money"),
            "revenue_drivers": bm.get("revenue_streams"),
            "customer_retention_hypothesis": customers.get("retention"),
            "capital_allocation": capital.get("assessment"),
            "long_term_value_creation": runway.get("growth_drivers"),
        },
        "capital_cycle": cycle,
        "customer_economics": customers,
        "pricing_power": pricing,
        "management": mgmt,
        "capital_allocation": capital,
        "growth": runway,
        "competitive_outlook": {
            "framework": "Competitive Outlook",
            "industry_phase_hypothesis": five.get("industry_attractiveness"),
            "disruption_watch": list(biz_risks.get("primary_risks") or [])[:3],
            "improving": (moat.get("trajectory") == "Improving")
            or (moat.get("durability") in {"Strong", "Improving"}),
            "why_improving_or_not": moat.get("assessment"),
            "positioning": evidence.get("competitive_position") or "Peer-relative franchise position",
            "outlook": (
                "Constructive"
                if (moat.get("durability") in {"Strong", "Improving"})
                else "Challenged"
                if moat.get("durability") in {"Weak", "Declining"}
                else "Mixed"
            ),
            "summary": moat.get("assessment") or five.get("industry_attractiveness") or "",
        },
        "risks": biz_risks,
        "knowledge_hits": list(moat.get("sources") or [])[:8],
    }


# Backward-compatible name
apply_frameworks = apply_all

__all__ = ["apply_all", "apply_frameworks"]
