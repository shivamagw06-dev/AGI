"""Senior IC depth evaluation bank (HELD OUT).

Tests quantification, sensitivity, bank-grade credit, timed macro chains,
ranked flags, investigative questions, committee debate, second-order effects,
and confidence calibration.

NEVER import into matchers/composers. NEVER train on these questions.
"""

from __future__ import annotations

from typing import Any

NEVER_TRAIN = True
EVALUATION_ONLY = True
CASE_ID = "ic_senior_depth_v1"
TOTAL_RUBRIC_POINTS = 180

QUESTIONS: list[dict[str, Any]] = [
    {
        "id": "D01",
        "marks": 20,
        "mode_hint": "ic_quant_value_creation",
        "question": (
            "Did capital allocation create shareholder value? Estimate ROIC, estimate WACC, "
            "quantify how large the value destruction/creation is, and say whether it looks temporary or structural. "
            "No Buy/Sell/Hold."
        ),
        "must_include": ["roic", "wacc", "temporary", "structural", "%"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "D02",
        "marks": 20,
        "mode_hint": "ic_valuation_sensitivity",
        "question": (
            "Which assumptions create the biggest valuation sensitivity? Consider WACC +1%, "
            "terminal growth −1%, margin recovery delayed two years, and working-capital normalisation delayed. "
            "Rank which changes valuation the most."
        ),
        "must_include": ["wacc", "terminal", "margin", "working capital", "sensitivity"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "D03",
        "marks": 20,
        "mode_hint": "ic_bank_grade_credit",
        "question": (
            "Bank-grade credit committee discussion: debt maturity ladder, interest coverage, "
            "EBITDA/debt, debt/FCF, refinancing probability, and liquidity runway."
        ),
        "must_include": [
            "maturity ladder",
            "interest coverage",
            "ebitda",
            "refinancing probability",
            "liquidity runway",
        ],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "D04",
        "marks": 20,
        "mode_hint": "ic_macro_timing_chain",
        "question": (
            "Explain the transmission mechanism of an RBI cut with timing: over 6 months, 18 months, and 3 years — "
            "through borrowing costs, refinancing, interest expense, cash flow and valuation."
        ),
        "must_include": ["6 months", "18 months", "3 years", "refinanc", "valuation"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "D05",
        "marks": 20,
        "mode_hint": "ic_rank_red_flags",
        "question": (
            "Rank which red flag matters most among cash conversion, debt, goodwill, inventory and receivables. "
            "Force prioritisation."
        ),
        "must_include": ["cash conversion", "debt", "goodwill", "inventory", "receivable", "rank"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "D06",
        "marks": 20,
        "mode_hint": "ic_investigative_questions",
        "question": (
            "What don't we know? Provide 20–30 investigative questions covering receivables, inventory obsolescence, "
            "maintenance vs growth capex, contract asset ageing, and synergy tracking."
        ),
        "must_include": ["receivable", "inventory", "capex", "synergy", "contract"],
        "must_not_include": ["buy", "sell"],
        "min_questions": 20,
    },
    {
        "id": "D07",
        "marks": 20,
        "mode_hint": "ic_committee_debate",
        "question": (
            "Simulate disagreement: Growth Committee, Credit Committee, Value Committee, Risk Committee, then Chair — "
            "why Committee A outweighs Committee B. Make them debate. No Buy/Sell/Hold."
        ),
        "must_include": [
            "growth committee",
            "credit committee",
            "value committee",
            "risk committee",
            "chair",
        ],
        "must_not_include": ["buy now", "sell now"],
    },
    {
        "id": "D08",
        "marks": 20,
        "mode_hint": "ic_second_order_macro",
        "question": (
            "Oil +44%: give second-order effects — not only margins. Chain through inflation, rates, discount rates, "
            "valuation, industrial demand, working capital and credit quality."
        ),
        "must_include": [
            "inflation",
            "discount",
            "valuation",
            "demand",
            "working capital",
            "credit",
        ],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "D09",
        "marks": 20,
        "mode_hint": "ic_confidence_calibration",
        "question": (
            "You assigned about 70% confidence to cash/credit stress. Why 70%? Why not 40%? Why not 90%? "
            "Give evidence-based confidence calibration."
        ),
        "must_include": ["70%", "40%", "90%", "evidence"],
        "must_not_include": ["buy", "sell"],
    },
]

assert sum(int(q["marks"]) for q in QUESTIONS) == TOTAL_RUBRIC_POINTS
assert NEVER_TRAIN is True
