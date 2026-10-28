"""Synthesize financial frameworks into institutional WHY language."""

from __future__ import annotations

from typing import Any

_BAD = (
    "revenue increased",
    "revenue grew",
    "margins improved",
    "debt reduced",
    "roe increased",
)


def _scrub(text: str) -> str:
    out = text
    lower = out.lower()
    for bad in _BAD:
        if bad in lower:
            idx = lower.find(bad)
            out = (out[:idx] + out[idx + len(bad) :]).strip(" .,")
            lower = out.lower()
    return out


def synthesize(
    *,
    company: str,
    frameworks: dict[str, Any],
    learning: dict[str, Any],
    benchmarks: dict[str, Any],
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    profit = frameworks.get("profitability") or {}
    rets = frameworks.get("returns") or {}
    growth = frameworks.get("growth_quality") or {}
    earnings = frameworks.get("earnings_quality") or {}
    cash = frameworks.get("cash_flow") or {}
    bs = frameworks.get("balance_sheet") or {}
    capital = frameworks.get("capital_allocation") or {}
    durable = frameworks.get("durability") or {}
    trends = frameworks.get("trends") or {}
    cases = learning.get("cases") or {}
    archetype = learning.get("archetype") or {}
    historical = learning.get("historical") or {}
    dna = learning.get("financial_dna") or {}

    support = 0
    support += 1 if rets.get("attractive") else 0
    support += 1 if earnings.get("trusted") else 0
    support += 1 if cash.get("cash_conversion") == "Improving" else 0
    support += 1 if bs.get("resilient") else 0
    support += 1 if capital.get("shareholder_value_created") else 0
    support += 1 if durable.get("recession_ready") else 0
    support -= 1 if cash.get("cash_conversion") == "Watch" else 0

    if support >= 3:
        stance = "Bullish"
    elif support <= 0:
        stance = "Bearish"
    else:
        stance = "Neutral"

    core = _scrub(
        f"{rets.get('assessment') or ''} {cash.get('assessment') or ''} {earnings.get('assessment') or ''}"
    ).strip()
    hist = str(historical.get("historical_narrative") or "").strip()
    resemblance = str(cases.get("resemblance") or "").strip()

    if stance == "Bullish":
        ownership = (
            f"Yes — the financial statements support the investment thesis for {company}, "
            "because earnings durability, cash conversion and capital returns currently align."
        )
    elif stance == "Bearish":
        ownership = (
            f"No — on present evidence, the financial statements do not adequately support the investment thesis "
            f"for {company}; cash conversion, returns or balance-sheet resilience remain too weak."
        )
    else:
        ownership = (
            f"Partially — {company}'s financial file is credible but not yet decisive in confirming "
            "durable economic value creation behind the investment thesis."
        )

    executive = _scrub(
        " ".join(x for x in (ownership, hist, core, resemblance) if x)
    ).strip()

    # Example-quality rewrite cue for ROE/leverage
    if rets.get("attractive") and bs.get("resilient"):
        executive = (
            executive
            + " Return on equity strength is more consistent with profitability than with added leverage, "
            "which is the higher-quality path for shareholder returns."
        )

    reasoning = [
        {"question": "Is profitability improving, and is it structural?", "answer": profit.get("assessment")},
        {"question": "Are returns attractive and persistent?", "answer": rets.get("assessment")},
        {"question": "Is growth genuine, profitable and sustainable?", "answer": growth.get("assessment")},
        {"question": "Can reported earnings be trusted?", "answer": earnings.get("assessment")},
        {"question": "Does accounting profit convert into cash?", "answer": cash.get("assessment")},
        {"question": "How resilient is the balance sheet?", "answer": bs.get("assessment")},
        {"question": "Has capital allocation created shareholder value?", "answer": capital.get("assessment")},
        {"question": "Could the business withstand a recession?", "answer": durable.get("assessment")},
        {"question": "What financial archetype applies?", "answer": archetype.get("template_reasoning")},
        {"question": "Do the financial statements support the investment thesis?", "answer": ownership},
    ]

    strengths = []
    if rets.get("attractive"):
        strengths.append("Returns on capital appear attractive without clear leverage dependence")
    if earnings.get("trusted"):
        strengths.append("Earnings quality signals align with cash conversion")
    if cash.get("cash_conversion") == "Improving":
        strengths.append("Cash generation is improving versus accounting profit")
    if bs.get("resilient"):
        strengths.append("Balance-sheet resilience supports downturn durability")
    if not strengths:
        strengths = ["Financial quality under institutional review"]

    weaknesses = []
    if cash.get("cash_conversion") == "Watch":
        weaknesses.append("Cash conversion still needs confirmation versus reported earnings")
    if not bs.get("resilient"):
        weaknesses.append("Leverage or liquidity resilience is not yet institutional-grade")
    if not capital.get("shareholder_value_created"):
        weaknesses.append("Capital allocation value creation not clearly evidenced")
    if not weaknesses:
        weaknesses = ["Incremental ROIC persistence", "Working-capital volatility"]

    assumptions = [
        "Assembled financial metrics and narrative represent current reporting reality.",
        "Cash conversion and return signals are more informative than single-period totals.",
        "Case analogues are directional pattern guides, not identity claims.",
        benchmarks.get("assessment") or "Peer benchmarking is qualitative where named peers are incomplete.",
    ]
    uncertainties = [
        "Multi-year versus quarterly inflection points may still be incompletely separated.",
        "One-off items could distort trailing margins and returns.",
        "Incremental returns on new capital through the next cycle remain partly unobserved.",
    ]
    missing = []
    if not profit.get("completed"):
        missing.append("Profitability detail")
    if not cash.get("completed"):
        missing.append("Cash flow detail")
    if not earnings.get("completed"):
        missing.append("Earnings quality detail")

    return {
        "executive_opinion": executive,
        "primary_question_answer": ownership,
        "stance": stance,
        "strengths": strengths[:5],
        "weaknesses": weaknesses[:5],
        "reasoning_steps": reasoning,
        "assumptions": [a for a in assumptions if a][:6],
        "uncertainties": uncertainties,
        "missing_evidence": missing,
        "financial_quality": {
            "grade": "High" if stance == "Bullish" else "Weak" if stance == "Bearish" else "Adequate",
            "summary": executive,
            "supports_thesis": stance != "Bearish",
            "trend": trends.get("overall"),
        },
        "lessons_learned": list(historical.get("lessons_learned") or [])[:8],
        "component_trajectories": historical.get("component_trajectories") or trends.get("components") or {},
        "dna_summary": dna.get("summary"),
    }
