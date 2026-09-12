"""The Phase 2.6 brief's own 'Mission' questions, plus every named term
across all 8 modules — must resolve without retrieval, without an LLM,
using only the deterministic concept library."""

from __future__ import annotations

import pytest

from financial_concepts.lookup import explain

MISSION_QUESTIONS = [
    "What is the DuPont Model?",
    "Why do banks trade on Price-to-Book?",
    "What is Enterprise Value?",
    "What is Economic Profit?",
    "What is EVA?",
    "What is Residual Income?",
    "What is Free Cash Flow Yield?",
    "What is NOPAT?",
]


@pytest.mark.parametrize("question", MISSION_QUESTIONS)
def test_mission_question_resolves_deterministically(question):
    result = explain(question)
    assert result["found"], f"Mission question not covered: {question!r}"
    assert result["confidence"] >= 0.9
    assert result["evidence_level"]


# Module 1 — Corporate Finance
MODULE_1_TERMS = [
    "Enterprise Value", "Market Capitalization", "Net Debt", "Capital Structure",
    "Cost of Debt", "Cost of Equity", "WACC", "Beta", "Equity Risk Premium",
    "Terminal Value", "NOPAT", "Economic Profit", "Residual Income",
    "Invested Capital", "Incremental ROIC", "Cash Conversion Cycle",
    "Working Capital", "Maintenance Capex", "Growth Capex",
]

# Module 2 — Ratio Intelligence
MODULE_2_TERMS = [
    "DuPont Model", "ROE decomposition", "ROA decomposition", "Operating Leverage",
    "Financial Leverage", "Interest Coverage", "Fixed Charge Coverage",
    "Cash Conversion", "Asset Turnover", "Capital Turnover", "Inventory Days",
    "Receivable Days", "Payable Days", "Cash Cycle", "Dividend Coverage", "FCF Conversion",
]

# Module 3 — Valuation
MODULE_3_TERMS = [
    "Enterprise Value", "Equity Value", "EV vs Market Cap", "EV/EBITDA", "EV/Sales",
    "P/E", "PEG", "P/B", "Dividend Yield", "FCF Yield", "Residual Income",
    "SOTP", "DCF", "Terminal Growth", "Exit Multiple",
]

# Module 4 — Banking
MODULE_4_TERMS = [
    "Book Value", "Tangible Book", "NIM", "CASA", "GNPA", "NNPA",
    "Provision Coverage", "CET1", "Risk Weighted Assets", "Cost of Funds",
    "Loan Growth", "Deposit Franchise",
]

# Module 5 — Cash Flow
MODULE_5_TERMS = [
    "Owner Earnings", "Free Cash Flow", "Levered FCF", "Unlevered FCF",
    "Working Capital Release", "Working Capital Absorption", "Capex Intensity",
    "Cash Burn", "Runway",
]

# Module 6 — Capital Allocation
MODULE_6_TERMS = [
    "ROIC", "Economic Moat", "Share Buyback", "Dividend Policy",
    "Capital Recycling", "Reinvestment Rate", "Payout Ratio", "Acquisition Returns",
]

# Module 7 — Credit
MODULE_7_TERMS = [
    "Debt Service Coverage", "Debt Maturity", "Liquidity", "Refinancing Risk",
    "Covenants", "Credit Ratings", "Default Risk",
]

# Module 8 — Market
MODULE_8_TERMS = [
    "Bull Market", "Bear Market", "Risk Premium", "Yield Curve", "Duration",
    "Inflation", "Real Rates", "Nominal Rates", "Volatility",
]

# Module 13 examples not already covered above
MODULE_13_EXTRA_TERMS = [
    "Capital Employed", "Contribution Margin", "Asset Intensity", "Capital Intensity",
    "Network Effect", "Switching Cost",
]

ALL_NAMED_TERMS = (
    MODULE_1_TERMS + MODULE_2_TERMS + MODULE_3_TERMS + MODULE_4_TERMS
    + MODULE_5_TERMS + MODULE_6_TERMS + MODULE_7_TERMS + MODULE_8_TERMS
    + MODULE_13_EXTRA_TERMS
)


@pytest.mark.parametrize("term", sorted(set(ALL_NAMED_TERMS)))
def test_every_named_brief_term_is_covered(term):
    result = explain(f"What is {term}?")
    assert result["found"], f"Named Phase 2.6 term not covered: {term!r}"
