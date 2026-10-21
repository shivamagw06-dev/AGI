"""Framework 6 — Customer Economics."""

from __future__ import annotations

from typing import Any

from institutional_analysts.business.brain._text import as_list, blob_of, txt


def assess(evidence: dict[str, Any]) -> dict[str, Any]:
    name = evidence.get("company") or "the company"
    brand = txt(evidence.get("brand"))
    pricing = txt(evidence.get("pricing_power"))
    advantages = as_list(evidence.get("advantages"), limit=5)
    drivers = as_list(evidence.get("revenue_drivers"), limit=5)
    b = blob_of(brand, pricing, advantages, drivers, evidence.get("business_model"))

    acquisition = (
        "Acquisition leverage comes from brand trust and distribution density, lowering effective CAC over time"
        if any(k in b for k in ("brand", "distribution", "trust", "franchise"))
        else "Customer acquisition cost must be earned back through retention and cross-sell"
    )
    retention = (
        brand
        or "Customers stay when product trust, convenience and switching frictions remain intact."
    )
    ltv = (
        f"Lifetime value compounds when {name} deepens relationships across products rather than winning one-off transactions."
    )
    switching = (
        "Switching behaviour is muted by relationship depth, product bundling and trust"
        if any(k in b for k in ("switch", "retention", "sticky", "casa", "franchise", "trust"))
        else "Switching risk rises if products become undifferentiated"
    )
    quality = (
        "Revenue quality is supported by relationship and recurring characteristics"
        if any(k in b for k in ("deposit", "fee", "recurring", "franchise", "retention"))
        else "Revenue quality depends on repeat purchase behaviour and mix"
    )

    why_loyal = (
        f"Customers remain loyal to {name} primarily because {retention.lower().rstrip('.')} "
        f"— not because of promotional intensity alone."
    )

    return {
        "framework": "Customer Economics",
        "completed": True,
        "customer_acquisition": acquisition,
        "retention": retention,
        "lifetime_value": ltv,
        "pricing": pricing or "Pricing power must be evidenced through mix and retention, not slogans.",
        "repeat_purchases": "Repeat / deepening relationships are central to franchise economics.",
        "switching_behaviour": switching,
        "revenue_quality": quality,
        "why_customers_are_loyal": why_loyal,
        "assessment": why_loyal,
    }
