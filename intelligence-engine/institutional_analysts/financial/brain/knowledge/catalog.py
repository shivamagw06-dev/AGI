"""Financial Analyst knowledge catalog — institutional finance frameworks."""

from __future__ import annotations

from typing import Any

KNOWLEDGE_DOMAINS = [
    "ROIC Tree",
    "DuPont Analysis",
    "Cash Conversion Cycle",
    "Working Capital",
    "Sloan Accrual Ratio",
    "Piotroski F Score",
    "Altman Z Score",
    "Beneish M Score",
    "Economic Profit",
    "Free Cash Flow",
    "Capital Allocation",
    "Earnings Quality",
    "Margin Expansion",
]

MISSION = (
    "Determine whether reported financial performance represents durable economic value creation."
)

PRIMARY_QUESTION = "Do the financial statements support the investment thesis?"

CORE_QUESTIONS = [
    "Is growth sustainable?",
    "Are profits high quality?",
    "Is cash flow improving?",
    "Can returns remain high?",
    "How resilient is the balance sheet?",
    "Has capital allocation created shareholder value?",
]


def knowledge_pack(ticker: str | None = None) -> dict[str, Any]:
    pack: dict[str, Any] = {
        "analyst": "Financial Analyst",
        "mission": MISSION,
        "primary_question": PRIMARY_QUESTION,
        "domains": list(KNOWLEDGE_DOMAINS),
        "core_questions": list(CORE_QUESTIONS),
        "never_answers": [
            "brand / moat commentary",
            "valuation attractiveness",
            "macro policy outlook",
            "tape / momentum calls",
        ],
    }
    try:
        from academy.books.flags import flag_books_v3
        from academy.books.v3.production import analyst_base

        if flag_books_v3():
            pack["academy_institutional"] = analyst_base(
                "financial",
                question="ROIC cash conversion earnings quality capital allocation",
            )
    except Exception:
        pass
    try:
        from peer_intelligence.flags import is_enabled as pil_enabled

        if pil_enabled():
            pack["peer_intelligence"] = {
                "enabled": True,
                "rule": "Financial conclusions must reference peer rank, history, or sector percentile before judgement",
                "soft_slice": "peer_intelligence.production.soft_slice_for_analyst(ticker, analyst='financial')",
            }
            if ticker:
                from peer_intelligence.production import soft_slice_for_analyst as pil_slice

                pack["peer_intelligence"].update(
                    (pil_slice(ticker, analyst="financial") or {}).get("peer_intelligence") or {}
                )
    except Exception:
        pass
    try:
        from filing_intelligence.flags import is_enabled as fil_enabled

        if fil_enabled():
            pack["filing_intelligence"] = {
                "enabled": True,
                "rule": "Historical financial trends must originate from validated filing intelligence when available",
                "soft_slice": "filing_intelligence.production.soft_slice_for_analyst(ticker, analyst='financial')",
            }
            if ticker:
                from filing_intelligence.production import soft_slice_for_analyst as fil_slice

                pack["filing_intelligence"].update(
                    (fil_slice(ticker, analyst="financial") or {}).get("filing_intelligence") or {}
                )
    except Exception:
        pass
    try:
        from management_intelligence.flags import is_enabled as mii_enabled

        if mii_enabled():
            pack["management_intelligence"] = {
                "enabled": True,
                "rule": "Capital allocation and guidance credibility must use MII evidence",
                "soft_slice": "management_intelligence.production.soft_slice_for_analyst(ticker, analyst='financial')",
            }
            if ticker:
                from management_intelligence.production import soft_slice_for_analyst as mii_slice

                pack["management_intelligence"].update(
                    (mii_slice(ticker, analyst="financial") or {}).get("management_intelligence") or {}
                )
    except Exception:
        pass
    try:
        from filing_diff.flags import is_enabled as fdi_enabled

        if fdi_enabled():
            pack["filing_diff"] = {
                "enabled": True,
                "rule": "Financial what-changed must prefer FDI material changes",
            }
            if ticker:
                from filing_diff.production import soft_slice_for_analyst as fdi_slice

                pack["filing_diff"].update((fdi_slice(ticker, analyst="financial") or {}).get("filing_diff") or {})
    except Exception:
        pass
    try:
        from accounting_intelligence.flags import is_enabled as aci_enabled

        if aci_enabled():
            pack["accounting_intelligence"] = {
                "enabled": True,
                "rule": "Full ACI — ask whether reported numbers can be trusted, not what they were",
                "soft_slice": "accounting_intelligence.production.soft_slice_for_analyst(ticker, analyst='financial')",
            }
            if ticker:
                from accounting_intelligence.production import soft_slice_for_analyst as aci_slice

                pack["accounting_intelligence"].update(
                    (aci_slice(ticker, analyst="financial") or {}).get("accounting_intelligence") or {}
                )
    except Exception:
        pass
    return pack
