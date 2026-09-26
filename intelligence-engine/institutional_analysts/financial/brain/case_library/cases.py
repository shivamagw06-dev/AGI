"""Financial case library — compounders and weak financial quality (knowledge assets)."""

from __future__ import annotations

from typing import Any

STRONG_CASES: list[dict[str, Any]] = [
    {
        "id": "apple",
        "name": "Apple",
        "pattern": "High incremental margins + cash conversion + disciplined capital return",
        "outcome": "Sustained high returns on capital with powerful free-cash-flow generation",
        "lessons": ["Cash conversion confirms earnings quality in premium compounders."],
        "signals": ("cash", "margin", "return", "buyback", "fcf"),
    },
    {
        "id": "microsoft",
        "name": "Microsoft",
        "pattern": "Recurring revenue economics + expanding operating leverage + fortress balance sheet",
        "outcome": "Earnings durability improved as mix shifted to higher-visibility cash streams",
        "lessons": ["Recurring cash economics raise confidence in reported profit persistence."],
        "signals": ("recurring", "margin", "cash", "cloud", "operating leverage"),
    },
    {
        "id": "tcs",
        "name": "TCS",
        "pattern": "Negative/low working-capital intensity + high cash conversion + steady ROIC",
        "outcome": "Consistent free cash flow supported long-duration compounding",
        "lessons": ["Asset-light cash machines can sustain high returns without leverage dependency."],
        "signals": ("cash conversion", "roic", "working capital", "margin", "it services"),
    },
    {
        "id": "hdfc_bank",
        "name": "HDFC Bank",
        "pattern": "Return on equity supported by operating profitability with conservative leverage culture",
        "outcome": "Multi-year financial resilience across credit cycles",
        "lessons": ["ROE improvement is highest quality when leverage stays broadly stable."],
        "signals": ("roe", "nim", "cash", "capital", "credit", "deposit"),
    },
    {
        "id": "nestle",
        "name": "Nestlé",
        "pattern": "Stable margins + strong cash conversion + disciplined reinvestment",
        "outcome": "Defensive financial compounding through cycles",
        "lessons": ["Margin stability plus cash conversion marks staples financial quality."],
        "signals": ("margin", "cash", "stable", "working capital", "fmcg"),
    },
]

WEAK_CASES: list[dict[str, Any]] = [
    {
        "id": "kingfisher",
        "name": "Kingfisher Airlines",
        "pattern": "Weak cash conversion + leverage stress + capital allocation failure",
        "outcome": "Financial collapse despite brand presence",
        "lessons": ["Without cash generation and capital discipline, reported growth is not investable."],
        "signals": ("cash burn", "leverage", "debt", "stress", "loss"),
    },
    {
        "id": "yes_bank",
        "name": "Yes Bank (pre-crisis)",
        "pattern": "Rapid asset growth with weakening funding / asset-quality signals",
        "outcome": "Severe capital and confidence crisis",
        "lessons": ["Growth that outruns funding quality and underwriting discipline destroys equity."],
        "signals": ("asset growth", "stress", "capital", "npa", "funding"),
    },
    {
        "id": "ilfs",
        "name": "IL&FS",
        "pattern": "Complex leverage and refinancing dependence",
        "outcome": "Systemic funding failure",
        "lessons": ["Opaque leverage and maturity walls are thesis-breaking financial risks."],
        "signals": ("leverage", "maturity", "refinanc", "complex", "liquidity"),
    },
    {
        "id": "wirecard",
        "name": "Wirecard",
        "pattern": "Cash and earnings quality mismatch / accounting integrity failure",
        "outcome": "Fraudulent reporting destroyed the equity",
        "lessons": ["Cash confirmation is mandatory when growth and earnings look exceptional."],
        "signals": ("cash mismatch", "accounting", "aggress", "fraud", "anomaly"),
    },
    {
        "id": "evergrande",
        "name": "Evergrande",
        "pattern": "High leverage with cash-flow fragility",
        "outcome": "Liquidity and solvency crisis",
        "lessons": ["Leverage without durable cash generation is not financial quality."],
        "signals": ("leverage", "liquidity", "debt", "cash", "stress"),
    },
]


def match_cases(evidence: dict[str, Any], frameworks: dict[str, Any]) -> dict[str, Any]:
    from institutional_analysts.financial.brain._text import blob_of

    blob = blob_of(
        evidence.get("narrative"),
        evidence.get("financial_quality"),
        evidence.get("trend"),
        evidence.get("cash_flow"),
        evidence.get("debt"),
        evidence.get("roe"),
        evidence.get("monitors"),
        (frameworks.get("earnings_quality") or {}).get("assessment"),
        (frameworks.get("cash_flow") or {}).get("assessment"),
        (frameworks.get("balance_sheet") or {}).get("assessment"),
    )

    def score(case: dict[str, Any]) -> int:
        return sum(1 for s in case.get("signals") or () if s in blob)

    strong = sorted(((c, score(c)) for c in STRONG_CASES), key=lambda x: x[1], reverse=True)
    weak = sorted(((c, score(c)) for c in WEAK_CASES), key=lambda x: x[1], reverse=True)
    top_s = [
        {"id": c["id"], "name": c["name"], "pattern": c["pattern"], "outcome": c["outcome"], "lessons": c["lessons"], "match_score": sc}
        for c, sc in strong if sc > 0
    ][:3] or [
        {"id": STRONG_CASES[0]["id"], "name": STRONG_CASES[0]["name"], "pattern": STRONG_CASES[0]["pattern"], "outcome": STRONG_CASES[0]["outcome"], "lessons": STRONG_CASES[0]["lessons"], "match_score": 0}
    ]
    top_w = [
        {"id": c["id"], "name": c["name"], "pattern": c["pattern"], "outcome": c["outcome"], "lessons": c["lessons"], "match_score": sc}
        for c, sc in weak if sc > 0
    ][:3] or [
        {"id": WEAK_CASES[0]["id"], "name": WEAK_CASES[0]["name"], "pattern": WEAK_CASES[0]["pattern"], "outcome": WEAK_CASES[0]["outcome"], "lessons": WEAK_CASES[0]["lessons"], "match_score": 0}
    ]

    eq_trusted = bool((frameworks.get("earnings_quality") or {}).get("trusted"))
    bs_ok = bool((frameworks.get("balance_sheet") or {}).get("resilient"))
    if eq_trusted and bs_ok:
        resemblance = (
            f"Financial pattern currently resembles {top_s[0]['name']} more than {top_w[0]['name']}."
        )
    else:
        resemblance = (
            f"On weaker cash / leverage / earnings-quality signals, the pattern risks resembling "
            f"{top_w[0]['name']} more than {top_s[0]['name']}."
        )

    lessons: list[str] = []
    for row in top_s[:2] + top_w[:2]:
        for lesson in row.get("lessons") or []:
            if lesson not in lessons:
                lessons.append(lesson)

    return {
        "strong_cases": top_s,
        "weak_cases": top_w,
        "resemblance": resemblance,
        "lessons_from_cases": lessons[:6],
        "primary_compounder_analogue": top_s[0]["name"],
        "primary_failure_analogue": top_w[0]["name"],
    }
