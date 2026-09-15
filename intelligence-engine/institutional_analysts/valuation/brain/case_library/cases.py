"""Valuation case library — premium compounders, overvalued growth, deep value."""

from __future__ import annotations

from typing import Any

from institutional_analysts.valuation.brain._text import blob_of

PREMIUM_CASES = [
    {
        "id": "apple",
        "name": "Apple",
        "pattern": "Premium multiple sustained by cash compounding and high capital efficiency",
        "market_expectations": "Persistence of high incremental returns and buyback-supported EPS growth",
        "outcome": "Premium often justified when cash delivery matched expectations",
        "lessons": ["Premium multiples can be rational if cash flows compound faster than the market fears."],
        "signals": ("premium", "cash", "compound", "efficiency", "growth"),
    },
    {
        "id": "microsoft",
        "name": "Microsoft",
        "pattern": "High multiple supported by recurring cash economics",
        "market_expectations": "Durable growth with high visibility cash streams",
        "outcome": "Valuation stayed elevated while expectations were repeatedly met",
        "lessons": ["Meeting embedded expectations matters more than starting multiple level."],
        "signals": ("recurring", "premium", "growth", "cash", "visibility"),
    },
    {
        "id": "nestle",
        "name": "Nestlé",
        "pattern": "Defensive premium for stability and cash conversion",
        "market_expectations": "Low-teens growth with resilient margins",
        "outcome": "Premium compressed mainly when growth or margins disappointed",
        "lessons": ["Defensive premiums shrink quickly if growth undershoots."],
        "signals": ("defensive", "premium", "stable", "cash", "margin"),
    },
    {
        "id": "asian_paints",
        "name": "Asian Paints",
        "pattern": "Long-duration premium for growth + returns consistency",
        "market_expectations": "Above-sector growth with high capital efficiency",
        "outcome": "Rich multiples required near-perfect delivery",
        "lessons": ["Long-duration premiums leave thin margin of safety on any execution miss."],
        "signals": ("premium", "growth", "efficiency", "india", "consistency"),
    },
    {
        "id": "hdfc_bank",
        "name": "HDFC Bank",
        "pattern": "Quality franchise often priced at a mid-to-premium band versus history",
        "market_expectations": "Steady growth with resilient returns on equity / capital",
        "outcome": "Valuation tracked delivery of growth and funding-cost assumptions",
        "lessons": ["Bank valuations hinge on whether growth and return assumptions stay realistic."],
        "signals": ("bank", "premium", "roe", "growth", "mid-band", "history"),
    },
]

OVERVALUED_CASES = [
    {
        "id": "cisco_dotcom",
        "name": "Cisco (dot-com)",
        "pattern": "Extreme growth expectations embedded in multiples",
        "market_expectations": "Perpetual hyper-growth",
        "outcome": "Multiple collapsed when growth normalised",
        "lessons": ["When price requires perfection, valuation risk dominates fundamental quality."],
        "signals": ("euphoria", "hyper", "extreme", "growth", "compression"),
    },
    {
        "id": "nifty_euphoria",
        "name": "Market euphoria episodes",
        "pattern": "Sector / market-wide multiple expansion beyond cash-flow support",
        "market_expectations": "Optimistic growth priced broadly",
        "outcome": "Mean reversion in multiples",
        "lessons": ["Multiple expansion without cash-flow support is not durable return fuel."],
        "signals": ("euphoria", "expansion", "rich", "broad", "re-rating"),
    },
]

DEEP_VALUE_CASES = [
    {
        "id": "cyclical_recovery",
        "name": "Selected cyclical recoveries",
        "pattern": "Depressed multiples into trough cash flows",
        "market_expectations": "Pessimistic near-term cash flows",
        "outcome": "Returns came from both earnings recovery and multiple normalisation",
        "lessons": ["Deep value works when trough assumptions are too pessimistic versus normalised cash flows."],
        "signals": ("depressed", "trough", "cyclical", "recovery", "normalisation"),
    },
]


def match_cases(evidence: dict[str, Any], frameworks: dict[str, Any]) -> dict[str, Any]:
    blob = blob_of(
        evidence.get("narrative"),
        evidence.get("margin_of_safety"),
        evidence.get("peer_comparison"),
        evidence.get("historical"),
        (frameworks.get("market_expectations") or {}).get("assessment"),
        (frameworks.get("margin_of_safety") or {}).get("assessment"),
    )
    premium = "Premium" in str((frameworks.get("market_expectations") or {}).get("premium_or_discount") or "")

    def score(case: dict[str, Any]) -> int:
        return sum(1 for s in case.get("signals") or () if s in blob)

    prem = sorted(((c, score(c)) for c in PREMIUM_CASES), key=lambda x: x[1], reverse=True)
    over = sorted(((c, score(c)) for c in OVERVALUED_CASES), key=lambda x: x[1], reverse=True)
    deep = sorted(((c, score(c)) for c in DEEP_VALUE_CASES), key=lambda x: x[1], reverse=True)

    top_p = [{"name": c["name"], "pattern": c["pattern"], "outcome": c["outcome"], "lessons": c["lessons"], "match_score": s} for c, s in prem if s > 0][:2] or [
        {"name": PREMIUM_CASES[-1]["name"], "pattern": PREMIUM_CASES[-1]["pattern"], "outcome": PREMIUM_CASES[-1]["outcome"], "lessons": PREMIUM_CASES[-1]["lessons"], "match_score": 0}
    ]
    top_o = [{"name": c["name"], "pattern": c["pattern"], "outcome": c["outcome"], "lessons": c["lessons"], "match_score": s} for c, s in over if s > 0][:2] or [
        {"name": OVERVALUED_CASES[0]["name"], "pattern": OVERVALUED_CASES[0]["pattern"], "outcome": OVERVALUED_CASES[0]["outcome"], "lessons": OVERVALUED_CASES[0]["lessons"], "match_score": 0}
    ]
    top_d = [{"name": c["name"], "pattern": c["pattern"], "outcome": c["outcome"], "lessons": c["lessons"], "match_score": s} for c, s in deep if s > 0][:1]

    if premium:
        resemblance = (
            f"Valuation pattern currently resembles {top_p[0]['name']} more than {top_o[0]['name']} "
            "only if cash-flow delivery matches embedded expectations; otherwise compression risk rises."
        )
    else:
        resemblance = (
            f"Valuation pattern is closer to a mid-band / selective deep-value setup than to {top_o[0]['name']} euphoria, "
            f"with lessons from {top_p[0]['name']} on when premiums are earned."
        )

    lessons: list[str] = []
    for row in top_p + top_o + top_d:
        for lesson in row.get("lessons") or []:
            if lesson not in lessons:
                lessons.append(lesson)

    return {
        "premium_cases": top_p,
        "overvalued_cases": top_o,
        "deep_value_cases": top_d,
        "resemblance": resemblance,
        "lessons_from_cases": lessons[:6],
    }
