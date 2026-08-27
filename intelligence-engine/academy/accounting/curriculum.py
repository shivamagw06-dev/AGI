"""Minimalist Accounting (Damodaran) — course map with provenance anchors.

Teaching source cluster (investor accounting curriculum):
- Understanding Financial Statements (Damodaran)
- Financial Statement Analysis / Accounting Prep slides
- Measuring Earnings (Investment Valuation ch.9)

Branded in Academy as Minimalist Accounting — Aswath Damodaran.
"""

from __future__ import annotations

from typing import Any

COURSE_ID = "damodaran_minimalist_accounting"
COURSE_TITLE = "Minimalist Accounting (Aswath Damodaran)"
COURSE_EDITION = "investor-curriculum-v1"
COURSE_AUTHOR = "Aswath Damodaran"

# Logical teaching chapters (university-style sequence for institutional analysts)
CHAPTERS: list[dict[str, Any]] = [
    {"chapter": 1, "title": "The Three Financial Statements", "printed_page": 1, "pdf_page": 1, "source": "finstate"},
    {"chapter": 2, "title": "Balance Sheet and Asset Measurement", "printed_page": 6, "pdf_page": 6, "source": "finstate"},
    {"chapter": 3, "title": "Financing Mix — Liabilities and Equity", "printed_page": 21, "pdf_page": 21, "source": "finstate"},
    {"chapter": 4, "title": "Income Statement — Revenue and Earnings", "printed_page": 35, "pdf_page": 35, "source": "finstate"},
    {"chapter": 5, "title": "Cash Flow Statement and Free Cash Flow", "printed_page": 4, "pdf_page": 4, "source": "finstate"},
    {"chapter": 6, "title": "Working Capital, Accruals, and Cash Conversion", "printed_page": 51, "pdf_page": 51, "source": "finstate"},
    {"chapter": 7, "title": "Return Measures — ROE, ROIC, Efficiency", "printed_page": 45, "pdf_page": 45, "source": "finstate"},
    {"chapter": 8, "title": "Analytical Adjustments — Leases, Capitalisation, SBC", "printed_page": 1, "pdf_page": 1, "source": "measuring_earnings"},
    {"chapter": 9, "title": "Earnings Quality Framework", "printed_page": 66, "pdf_page": 66, "source": "finstate"},
    {"chapter": 10, "title": "Accounting Red Flags and Risk Ratios", "printed_page": 52, "pdf_page": 52, "source": "finstate"},
]

CONCEPT_CHAPTER_MAP: dict[str, int] = {
    "income_statement": 4,
    "balance_sheet": 2,
    "cash_flow_statement": 5,
    "revenue_recognition": 4,
    "cogs": 4,
    "gross_profit": 4,
    "operating_expenses": 4,
    "ebitda": 4,
    "ebit": 4,
    "net_income": 4,
    "operating_cash_flow": 5,
    "free_cash_flow": 5,
    "depreciation": 2,
    "amortisation": 2,
    "inventory": 2,
    "accounts_receivable": 2,
    "accounts_payable": 3,
    "deferred_revenue": 4,
    "deferred_tax": 3,
    "goodwill": 2,
    "intangible_assets": 2,
    "capitalised_expenses": 8,
    "leases": 3,
    "share_based_compensation": 8,
    "minority_interest": 3,
    "working_capital": 6,
    "cash_conversion_cycle": 6,
    "earnings_quality": 9,
    "accruals": 6,
    "restatements": 10,
    "exceptional_items": 9,
    "accounting_estimates": 9,
    "impairment": 2,
    "provisions": 3,
    "roe": 7,
    "roic": 7,
    "roce": 7,
    "asset_turnover": 7,
    "interest_coverage": 10,
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
    raise KeyError(f"Unknown accounting chapter {chapter}")


def course_manifest() -> dict[str, Any]:
    return {
        "course_id": COURSE_ID,
        "title": COURSE_TITLE,
        "edition": COURSE_EDITION,
        "author": COURSE_AUTHOR,
        "mission": "Teach AGI how institutional investors read financial statements — not how accountants prepare them",
        "architecture_status": "v1.0.1 LOCKED",
        "chapter_count": len(CHAPTERS),
        "chapters": [chapter_meta(c["chapter"]) for c in CHAPTERS],
        "concept_chapter_map": CONCEPT_CHAPTER_MAP,
        "source_materials": [
            "Understanding Financial Statements (Damodaran)",
            "Financial Statement Analysis / Accounting Prep",
            "Measuring Earnings (Investment Valuation)",
        ],
        "not_a_summariser": True,
        "investor_perspective": True,
    }
