"""Reasoning Families — reusable habits, not memorised T1–T15 cases.

Every new question maps to a family. Exact gold cases remain training
examples; novel facts must use the family habit or first principles.
"""

from __future__ import annotations

from typing import Any

# Canonical family IDs (stable API).
CONTRADICTION = "contradiction"
EVIDENCE = "evidence"
CAUSALITY = "causality"
ACCOUNTING = "accounting"
VALUATION = "valuation"
UNCERTAINTY = "uncertainty"
SELF_CRITIQUE = "self_critique"
COMPARISON = "comparison"
DUAL_HYPOTHESIS = "dual_hypothesis"  # hardest institutional benchmark

FAMILIES: dict[str, dict[str, Any]] = {
    CONTRADICTION: {
        "label": "Contradiction",
        "covers": (
            "Profit vs ROE",
            "Revenue vs Margin",
            "Demand vs Sales",
            "Volume vs Quality",
            "Growth vs Risk provisions",
        ),
        "habit": (
            "Two signals can both be real. Identify which measures quality vs scale, "
            "list alternative explanations, and avoid choosing without evidence."
        ),
    },
    EVIDENCE: {
        "label": "Evidence",
        "covers": ("Provider conflicts", "News vs filings", "Source hierarchy"),
        "habit": (
            "Do not average conflicting sources. Prefer official / verified data; "
            "keep confidence lower until confirmed."
        ),
    },
    CAUSALITY: {
        "label": "Causality",
        "covers": ("Rate changes", "Oil", "Inflation", "Macro → sector → company"),
        "habit": (
            "Map the causal chain by business model. One macro move rarely affects "
            "every industry the same way."
        ),
    },
    ACCOUNTING: {
        "label": "Accounting",
        "covers": ("Cash flow", "Working capital", "Inventory", "Receivables"),
        "habit": (
            "Accrual results and cash can diverge. Ask which balance-sheet or cash "
            "items absorb the difference before judging quality."
        ),
    },
    VALUATION: {
        "label": "Valuation",
        "covers": ("P/E", "EV/EBITDA", "DCF", "Multiple vs earnings"),
        "habit": (
            "A multiple is price relative to a base. Earnings and multiples can move "
            "in opposite directions when price does not keep pace with earnings."
        ),
    },
    UNCERTAINTY: {
        "label": "Uncertainty",
        "covers": ("Missing data", "Unknowns", "Incomplete evidence"),
        "habit": (
            "State what cannot be concluded. Do not fill gaps with invented certainty."
        ),
    },
    SELF_CRITIQUE: {
        "label": "Self-critique",
        "covers": ("Devil's advocate", "Assumptions", "Falsifiers"),
        "habit": (
            "Challenge the current view. List assumptions and what evidence would "
            "prove them wrong. Do not defend a thesis for its own sake."
        ),
    },
    COMPARISON: {
        "label": "Comparison",
        "covers": ("Company A vs Company B", "Same growth different quality"),
        "habit": (
            "One metric is never enough. Compare capital intensity, leverage, cash "
            "conversion, margins, allocation and industry context."
        ),
    },
    DUAL_HYPOTHESIS: {
        "label": "Dual Hypothesis",
        "covers": ("Multi-metric divergence", "Equally plausible narratives"),
        "habit": (
            "Hold two coherent explanations open. Show supporting and contradicting "
            "evidence for each. Do not decide which is correct."
        ),
    },
}

FAMILY_ORDER = (
    DUAL_HYPOTHESIS,
    SELF_CRITIQUE,
    UNCERTAINTY,
    EVIDENCE,
    VALUATION,
    ACCOUNTING,
    CAUSALITY,
    COMPARISON,
    CONTRADICTION,
)

__all__ = [
    "ACCOUNTING",
    "CAUSALITY",
    "COMPARISON",
    "CONTRADICTION",
    "DUAL_HYPOTHESIS",
    "EVIDENCE",
    "FAMILIES",
    "FAMILY_ORDER",
    "SELF_CRITIQUE",
    "UNCERTAINTY",
    "VALUATION",
]
