"""Positive business case studies — knowledge assets, not engines."""

from __future__ import annotations

from typing import Any

SUCCESS_CASES: list[dict[str, Any]] = [
    {
        "id": "apple",
        "name": "Apple",
        "archetype_hints": ["consumer_internet", "consumer_staples_like_brand"],
        "drivers": ["Brand", "Pricing power", "Switching costs", "Ecosystem"],
        "chain": ["Brand", "Pricing", "Switching Costs", "Outcome", "Lessons"],
        "outcome": "Sustained premium pricing and high incremental returns on a locked-in installed base.",
        "lessons": [
            "Brand plus switching costs can convert product cycles into durable economic profit.",
            "Pricing power is strongest when the customer leaves an ecosystem, not a SKU.",
        ],
        "signals": ("brand", "pricing", "switch", "ecosystem", "premium", "retention"),
    },
    {
        "id": "nestle",
        "name": "Nestlé",
        "archetype_hints": ["consumer_staples"],
        "drivers": ["Distribution", "Brand", "Working capital discipline", "Pricing"],
        "chain": ["Distribution", "Brand", "Working Capital", "Pricing", "Outcome", "Lessons"],
        "outcome": "Global distribution depth and brand trust produced resilient cash generation across cycles.",
        "lessons": [
            "Distribution reach multiplies brand; brand alone rarely compounds without route-to-market strength.",
            "Working-capital discipline turns staples volume into free cash rather than inventory drag.",
        ],
        "signals": ("distribution", "brand", "working capital", "staples", "fmcg", "pricing"),
    },
    {
        "id": "amazon",
        "name": "Amazon",
        "archetype_hints": ["consumer_internet"],
        "drivers": ["Scale", "Network effects", "Cloud adjacency", "Reinvestment"],
        "chain": ["Scale", "Network Effects", "Cloud", "Outcome", "Lessons"],
        "outcome": "Scale and network effects funded adjacent high-ROE platforms after a long reinvestment phase.",
        "lessons": [
            "Winner-takes-most economics may justify early cash burn when scale creates later pricing/cost power.",
            "Adjacencies work when they reuse the same distribution or infrastructure advantage.",
        ],
        "signals": ("scale", "network", "platform", "cloud", "marketplace", "reinvestment"),
    },
    {
        "id": "berkshire",
        "name": "Berkshire Hathaway",
        "archetype_hints": ["capital_allocator"],
        "drivers": ["Capital allocation", "Insurance float", "Owner orientation", "Patience"],
        "chain": ["Capital Allocation", "Float", "Owner Returns", "Outcome", "Lessons"],
        "outcome": "Decades of disciplined capital allocation compounded intrinsic business value.",
        "lessons": [
            "Capital allocation discipline can be a moat when reinvestment opportunities are scarce or expensive.",
            "Long-term ownership orientation beats empire-building acquisition calendars.",
        ],
        "signals": ("capital allocation", "disciplin", "conservative", "owner", "float", "compound"),
    },
]
