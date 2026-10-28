"""Framework 3 — Porter Five Forces."""

from __future__ import annotations

from typing import Any

from institutional_analysts.business.brain._text import as_list, blob_of, txt


def assess(evidence: dict[str, Any]) -> dict[str, Any]:
    name = evidence.get("company") or "the company"
    advantages = as_list(evidence.get("advantages"), limit=6)
    risks = as_list(evidence.get("business_risks"), limit=6)
    position = txt(evidence.get("competitive_position"))
    b = blob_of(advantages, risks, position, evidence.get("business_model"))

    rivalry = (
        "Elevated — peers compete aggressively on price, distribution and product breadth"
        if any(k in b for k in ("compet", "rival", "price war"))
        else "Moderate — oligopolistic or franchise-structured rivalry"
    )
    supplier = (
        "Material — concentrated inputs, funding or labour can pressure margins"
        if any(k in b for k in ("supplier", "funding", "labour", "input"))
        else "Moderate — diversified supply / funding options mute single-point pressure"
    )
    customer = (
        "Elevated where products are commoditised and switching is easy"
        if any(k in b for k in ("commodit", "price sensitive"))
        else "Contained where trust, switching costs and product differentiation retain customers"
    )
    substitutes = (
        "Present — alternative products or channels can capture incremental demand"
        if any(k in b for k in ("substitut", "disrupt", "fintech", "alternate"))
        else "Muted near-term where incumbency and regulation slow displacement"
    )
    entrants = (
        "Contained by scale, licenses, distribution and trust requirements"
        if any(k in b for k in ("scale", "license", "distribution", "brand", "network", "regulation"))
        else "Open — limited structural barriers to entry"
    )

    attractive_signals = sum(
        1
        for x in (entrants, customer, substitutes)
        if any(w in x.lower() for w in ("contained", "muted", "diversified"))
    )
    attractiveness = (
        "Attractive for long-term compounders"
        if attractive_signals >= 2 and "Elevated" not in rivalry
        else "Selectively attractive"
        if attractive_signals >= 1
        else "Challenging industry structure"
    )

    return {
        "framework": "Porter Five Forces",
        "completed": True,
        "competitive_rivalry": rivalry,
        "supplier_power": supplier,
        "customer_power": customer,
        "threat_of_substitutes": substitutes,
        "threat_of_new_entrants": entrants,
        "industry_attractiveness": attractiveness,
        "implication": (
            f"Industry structure around {name} supports durable economics when rivalry and substitution "
            "do not permanently erase returns on incremental capital."
        ),
        "assessment": attractiveness,
    }
