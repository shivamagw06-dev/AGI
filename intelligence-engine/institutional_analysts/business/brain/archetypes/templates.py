"""Business archetypes — reusable pattern templates."""

from __future__ import annotations

from typing import Any

ARCHETYPES: list[dict[str, Any]] = [
    {
        "id": "consumer_staples",
        "name": "Consumer Staples",
        "pattern": [
            "High brand",
            "High pricing power",
            "High cash generation",
            "Low disruption",
        ],
        "signals": ("brand", "staples", "fmcg", "distribution", "pricing", "cash", "repeat"),
        "implications": (
            "Ownership case rests on brand/distribution durability and pricing through inflation, "
            "not on cyclical volume spikes."
        ),
    },
    {
        "id": "commodity",
        "name": "Commodity Business",
        "pattern": [
            "Low differentiation",
            "Capacity cycles",
            "Low pricing power",
            "Capital intensive",
        ],
        "signals": ("commodity", "capacity", "capex", "undifferentiated", "cyclical", "price taker"),
        "implications": (
            "Returns are cycle-dependent; exceptional ownership requires cost leadership or "
            "disciplined capital spending through the capacity cycle."
        ),
    },
    {
        "id": "consumer_internet",
        "name": "Consumer Internet",
        "pattern": [
            "Network effects",
            "Winner takes most",
            "Cash burn initially",
            "Scale economics later",
        ],
        "signals": ("network", "platform", "marketplace", "ecosystem", "scale", "digital", "users"),
        "implications": (
            "Early losses can be rational only if network effects and switching costs later "
            "produce durable take rates or cost advantages."
        ),
    },
    {
        "id": "regulated_franchise",
        "name": "Regulated Franchise / Financial Franchise",
        "pattern": [
            "License / trust barriers",
            "Funding or distribution advantage",
            "Underwriting discipline",
            "Regulatory overlay",
        ],
        "signals": (
            "deposit",
            "franchise",
            "bank",
            "insurance",
            "license",
            "casa",
            "underwrit",
            "nim",
            "regulatory",
        ),
        "implications": (
            "Moat durability depends on low-cost funding, distribution density and underwriting — "
            "and can erode gradually via deposit competition even if structure remains intact."
        ),
    },
    {
        "id": "capital_allocator",
        "name": "Capital Allocator Compounder",
        "pattern": [
            "Owner orientation",
            "Reinvestment selectivity",
            "Balance-sheet conservatism",
            "Patience",
        ],
        "signals": ("capital allocation", "disciplin", "conservative", "reinvestment", "owner", "compound"),
        "implications": (
            "Business quality is inseparable from allocation skill; compare to disciplined allocators, "
            "not merely to sector volume leaders."
        ),
    },
]
