"""Framework 4 — Value Chain."""

from __future__ import annotations

from typing import Any

from institutional_analysts.business.brain._text import as_list, blob_of, txt


def assess(evidence: dict[str, Any]) -> dict[str, Any]:
    name = evidence.get("company") or "the company"
    model = txt(evidence.get("business_model"))
    drivers = as_list(evidence.get("revenue_drivers"), limit=5)
    advantages = as_list(evidence.get("advantages"), limit=5)
    b = blob_of(model, drivers, advantages, evidence.get("brand"), evidence.get("capital_allocation"))

    procurement = (
        "Funding / input sourcing advantage supports unit economics"
        if any(k in b for k in ("deposit", "funding", "procurement", "low-cost"))
        else "Procurement economics require ongoing discipline"
    )
    operations = (
        "Operating process quality and underwriting / production discipline create margin"
        if any(k in b for k in ("underwrit", "operat", "process", "efficiency"))
        else "Operations contribute when scale efficiencies outpace cost inflation"
    )
    distribution = (
        "Distribution reach is a primary value and margin locus"
        if any(k in b for k in ("distribution", "branch", "channel", "reach", "network"))
        else "Distribution effectiveness determines share of demand captured"
    )
    marketing = (
        "Brand and trust reduce acquisition friction and protect pricing"
        if any(k in b for k in ("brand", "trust", "franchise"))
        else "Marketing spend must convert into durable customer relationships"
    )
    service = (
        "Customer service and relationship depth sustain retention and cross-sell"
        if any(k in b for k in ("retention", "relationship", "service", "trust"))
        else "Service quality influences switching behaviour and lifetime value"
    )
    technology = (
        "Technology amplifies distribution and lowers marginal servicing cost"
        if any(k in b for k in ("digital", "tech", "data", "platform"))
        else "Technology investment is a supporting, not yet decisive, value lever"
    )

    value_loci = []
    for label, text in (
        ("Distribution", distribution),
        ("Brand / Marketing", marketing),
        ("Operations", operations),
        ("Procurement / Funding", procurement),
    ):
        if any(w in text.lower() for w in ("primary", "advantage", "create", "protect", "quality")):
            value_loci.append(label)

    return {
        "framework": "Value Chain",
        "completed": True,
        "procurement": procurement,
        "operations": operations,
        "distribution": distribution,
        "marketing": marketing,
        "customer_service": service,
        "technology": technology,
        "where_value_is_created": value_loci or ["Core franchise activities"],
        "where_margin_is_created": (
            f"{name} creates margin where distribution advantage, relationship depth and operating discipline "
            "convert demand into durable economic profit."
        ),
        "assessment": (
            f"Value accrues mainly in {', '.join((value_loci or ['core operations'])[:3]).lower()}, "
            "not in generic product description."
        ),
    }
