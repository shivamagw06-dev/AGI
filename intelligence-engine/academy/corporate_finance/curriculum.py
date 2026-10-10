"""Applied Corporate Finance (Damodaran) — course map with provenance.

Source: Applied Corporate Finance, Aswath Damodaran (4e manuscript/PDF).
PDF page anchors validated against local books/Damodaran_Applied_Corporate_Finance.pdf.
"""

from __future__ import annotations

from typing import Any

COURSE_ID = "damodaran_applied_corporate_finance"
COURSE_TITLE = "Applied Corporate Finance (Aswath Damodaran)"
COURSE_EDITION = "4e"
COURSE_AUTHOR = "Aswath Damodaran"

CHAPTERS: list[dict[str, Any]] = [
    {"chapter": 1, "title": "The Foundations", "printed_page": 1, "pdf_page": 8},
    {"chapter": 2, "title": "The Objective in Decision Making", "printed_page": 1, "pdf_page": 21},
    {"chapter": 3, "title": "The Basics of Risk", "printed_page": 1, "pdf_page": 93},
    {"chapter": 4, "title": "Risk Measurement and Hurdle Rates in Practice", "printed_page": 1, "pdf_page": 153},
    {"chapter": 5, "title": "Measuring Return on Investments", "printed_page": 1, "pdf_page": 269},
    {"chapter": 6, "title": "Project Interactions, Side Costs, and Side Benefits", "printed_page": 1, "pdf_page": 368},
    {"chapter": 7, "title": "Capital Structure: Overview of the Financing Decision", "printed_page": 1, "pdf_page": 457},
    {"chapter": 8, "title": "Capital Structure: The Optimal Financial Mix", "printed_page": 1, "pdf_page": 544},
    {"chapter": 9, "title": "Capital Structure: The Financing Details", "printed_page": 1, "pdf_page": 630},
    {"chapter": 10, "title": "Dividend Policy", "printed_page": 1, "pdf_page": 698},
    {"chapter": 11, "title": "Analyzing Cash Returned to Stockholders", "printed_page": 1, "pdf_page": 752},
    {"chapter": 12, "title": "Valuation: Principles and Practice", "printed_page": 1, "pdf_page": 820},
]

CONCEPT_CHAPTER_MAP: dict[str, int] = {
    "investment_principle": 1,
    "financing_principle": 1,
    "dividend_principle": 1,
    "firm_value_maximization": 2,
    "hurdle_rate": 4,
    "cost_of_equity": 4,
    "capm": 3,
    "beta": 4,
    "equity_risk_premium": 4,
    "country_risk_premium": 4,
    "cost_of_debt": 4,
    "wacc": 4,
    "capital_allocation": 5,
    "organic_reinvestment": 5,
    "debt_repayment": 9,
    "capital_raising": 9,
    "debt_vs_equity": 7,
    "financial_leverage": 7,
    "optimal_capital_structure": 8,
    "trade_off_theory": 8,
    "pecking_order_theory": 7,
    "agency_costs": 2,
    "financial_distress": 8,
    "npv": 5,
    "irr": 5,
    "payback_period": 5,
    "profitability_index": 5,
    "economic_profit": 5,
    "eva": 5,
    "roic_wacc_spread": 5,
    "incremental_roic": 5,
    "value_creation": 12,
    "value_destruction": 12,
    "dividend_policy": 10,
    "dividend_payout": 10,
    "retention_ratio": 10,
    "dividend_signalling": 10,
    "share_buybacks": 11,
    "eps_illusion": 11,
    "acquisition_synergies": 6,
    "acquisition_overpayment": 6,
    "integration_risk": 6,
    "acquisition_quality": 6,
    "corporate_lifecycle": 12,
}


def chapter_meta(chapter: int) -> dict[str, Any]:
    for row in CHAPTERS:
        if row["chapter"] == chapter:
            out = dict(row)
            out["book"] = COURSE_TITLE
            out["edition"] = COURSE_EDITION
            out["author"] = COURSE_AUTHOR
            out["course_id"] = COURSE_ID
            return out
    raise KeyError(f"Unknown ACF chapter {chapter}")


def course_manifest() -> dict[str, Any]:
    return {
        "course_id": COURSE_ID,
        "title": COURSE_TITLE,
        "edition": COURSE_EDITION,
        "author": COURSE_AUTHOR,
        "mission": "Teach AGI how companies create, preserve, and destroy shareholder value",
        "architecture_status": "v1.0.1 LOCKED",
        "chapter_count": len(CHAPTERS),
        "chapters": [chapter_meta(c["chapter"]) for c in CHAPTERS],
        "concept_chapter_map": CONCEPT_CHAPTER_MAP,
        "foundations": ["Investment Principle", "Financing Principle", "Dividend Principle"],
        "not_a_summariser": True,
        "investor_perspective": True,
    }
