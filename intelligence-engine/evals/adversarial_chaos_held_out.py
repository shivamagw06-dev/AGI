"""Adversarial Chaos evaluation bank — Phase 3–8.

CRITICAL RULES
--------------
1. NEVER import this module into matchers, composers, gold patterns, or adversarial detectors
   for the purpose of training / expanding templates from these exact strings.
2. NEVER train on these questions.
3. Use only for evaluation / scorecards.
4. A perfect score here means success on THIS adversarial set — not proof of unbounded
   "genuine reasoning" in the wild.
"""

from __future__ import annotations

from typing import Any

# Hand-authored adversarial cases (Tests 1–8 + consistency + fictional company).
ADVERSARIAL_CORE: list[dict[str, Any]] = [
    {
        "id": "A01",
        "phase": 3,
        "mode": "unknown_time_horizons",
        "question": (
            "A company's revenue has grown every year for five years, but it has declined "
            "for the last two quarters. Which trend deserves more weight and why?"
        ),
        "must_include": ["horizons", "quarters", "temporary"],
        "must_not_include": ["buy", "sell", "target price"],
        "require_no_forced_single_trend": True,
    },
    {
        "id": "A02",
        "phase": 3,
        "mode": "unknown_business_vs_valuation",
        "question": (
            "The business continues to improve, but the share price has doubled while earnings "
            "have grown only 15%. How should the business and valuation be assessed separately?"
        ),
        "must_include": ["separate", "valuation", "business"],
        "must_not_include": ["buy", "sell"],
        "require_separation": True,
    },
    {
        "id": "A03",
        "phase": 3,
        "mode": "unknown_missing_cashflow",
        "question": (
            "The company has not yet released its cash flow statement, but revenue and profit "
            "have both increased. What conclusions can and cannot be drawn?"
        ),
        "must_include": ["cannot", "cash", "revenue"],
        "must_not_include": ["cash generation improved"],
        "require_evidence_boundary": True,
    },
    {
        "id": "A04",
        "phase": 4,
        "mode": "cross_family_macro_sector",
        "question": (
            "Inflation is rising, the RBI increases interest rates, oil prices fall, and the "
            "rupee strengthens. How could these developments affect an airline, a private bank "
            "and an IT exporter differently?"
        ),
        "must_include": ["airline", "bank", "exporter", "decompos"],
        "must_not_include": ["one macro narrative that fits all"],
        "require_decomposition": True,
    },
    {
        "id": "A05",
        "phase": 4,
        "mode": "cross_family_dual_hypothesis",
        "question": (
            "Revenue increased, profit declined, debt fell, free cash flow improved and the "
            "share price rose. Construct two competing explanations and identify the evidence "
            "needed to distinguish between them."
        ),
        "must_include": ["explanation 1", "explanation 2", "distinguish"],
        "must_not_include": ["the correct explanation is"],
        "forbids_decision": True,
    },
    {
        "id": "A06",
        "phase": 5,
        "mode": "self_critique_assumptions",
        "question": (
            "After reaching your conclusion, list the three assumptions that have the greatest "
            "influence on it. For each assumption, explain what future evidence would invalidate it."
        ),
        "must_include": ["assumption 1", "assumption 2", "assumption 3", "invalidat"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "A07",
        "phase": 5,
        "mode": "self_critique_steelman",
        "question": (
            "If another analyst disagreed with your conclusion, what is the strongest evidence "
            "they could use to support the opposite view?"
        ),
        "must_include": ["opposite", "evidence"],
        "must_not_include": ["the other analyst is wrong"],
    },
    {
        "id": "A08",
        "phase": 6,
        "mode": "evidence_hierarchy_sources",
        "question": (
            "You have a company press release, an NSE filing, a Reuters article, a social media "
            "post and an investor presentation. One source claims a major acquisition, the others "
            "do not. How should AIG evaluate the evidence before updating its assessment?"
        ),
        "must_include": ["nse", "filing", "social media", "authoritative"],
        "must_not_include": ["treat social media as confirmed"],
        "require_hierarchy": True,
    },
    {
        "id": "A09",
        "phase": 7,
        "mode": "unknown_company_accounting",
        "question": (
            "ABC Manufacturing reported: Revenue +18%, Profit +5%, Inventory +42%, "
            "Receivables +38%, Debt unchanged, Share price +12%. No prior knowledge should be "
            "needed. What does this imply about earnings quality and cash conversion?"
        ),
        "must_include": ["inventory", "receivables", "cash"],
        "must_not_include": ["HDFC", "Infosys", "buy"],
        "require_no_real_company_recall": True,
    },
    {
        "id": "A10a",
        "phase": 8,
        "mode": "consistency_cash_vs_revenue",
        "consistency_group": "cash_vs_revenue",
        "question": "Why did free cash flow fall despite higher revenue?",
        "must_include": ["cash", "revenue"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "A10b",
        "phase": 8,
        "mode": "consistency_cash_vs_revenue",
        "consistency_group": "cash_vs_revenue",
        "question": "Explain why cash generation weakened even though sales improved.",
        "must_include": ["cash", "sales"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "A10c",
        "phase": 8,
        "mode": "consistency_cash_vs_revenue",
        "consistency_group": "cash_vs_revenue",
        "question": "Revenue rose but cash fell. Why?",
        "must_include": ["cash", "revenue"],
        "must_not_include": ["buy", "sell"],
    },
]

# Extra adversarial variants — still evaluation-only, never training data.
_ADVERSARIAL_VARIANTS: list[dict[str, Any]] = [
    {
        "id": "A11",
        "phase": 3,
        "mode": "unknown_time_horizons",
        "question": (
            "Operating profit compounded for a decade, yet the latest three months show a sharp drop. "
            "How should a long-horizon and short-horizon view be weighed together?"
        ),
        "must_include": ["horizon"],
        "must_not_include": ["buy"],
    },
    {
        "id": "A12",
        "phase": 3,
        "mode": "unknown_business_vs_valuation",
        "question": (
            "Return on capital is rising, but the stock now discounts growth far above the company's "
            "guided earnings path. Separate the operating story from the price story."
        ),
        "must_include": ["separate"],
        "must_not_include": ["buy"],
    },
    {
        "id": "A13",
        "phase": 4,
        "mode": "cross_family_macro_sector",
        "question": (
            "Inflation cools, the RBI still keeps rates high, oil jumps and the rupee weakens. "
            "Compare implications for an airline, a private bank and an IT exporter without one blended story."
        ),
        "must_include": ["airline", "bank"],
        "must_not_include": ["buy"],
        "require_decomposition": True,
    },
    {
        "id": "A14",
        "phase": 5,
        "mode": "self_critique_assumptions",
        "question": (
            "List the three assumptions with the greatest influence on a constructive outlook and "
            "the future evidence that would invalidate each."
        ),
        "must_include": ["assumption", "invalidat"],
        "must_not_include": ["buy"],
    },
    {
        "id": "A15",
        "phase": 6,
        "mode": "evidence_hierarchy_sources",
        "question": (
            "A social media post and a Reuters blurb claim a plant expansion; the NSE filing and "
            "company press release are silent. Rank the sources before changing the assessment."
        ),
        "must_include": ["filing", "social"],
        "must_not_include": ["confirmed by social media"],
        "require_hierarchy": True,
    },
]


def list_adversarial() -> list[dict[str, Any]]:
    return list(ADVERSARIAL_CORE) + list(_ADVERSARIAL_VARIANTS)


ADVERSARIAL_BANK: list[dict[str, Any]] = list_adversarial()

NEVER_TRAIN = True
EVALUATION_ONLY = True
BENCHMARK_TIER = "adversarial_chaos"

assert NEVER_TRAIN is True
assert all("question" in r and "mode" in r for r in ADVERSARIAL_BANK)

__all__ = [
    "ADVERSARIAL_BANK",
    "ADVERSARIAL_CORE",
    "BENCHMARK_TIER",
    "EVALUATION_ONLY",
    "NEVER_TRAIN",
    "list_adversarial",
]
