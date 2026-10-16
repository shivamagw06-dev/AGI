"""Valuation Analyst knowledge catalog."""

from __future__ import annotations

from typing import Any

KNOWLEDGE_DOMAINS = [
    "DCF",
    "Reverse DCF",
    "Residual Income",
    "Economic Value Added",
    "SOTP",
    "Comparable Companies",
    "Comparable Transactions",
    "Historical Multiples",
    "Margin of Safety",
    "Expected Return",
    "Monte Carlo",
    "Scenario Valuation",
]

MISSION = (
    "Determine whether the current market price is justified by expected future cash flows, "
    "growth, profitability and risk."
)

PRIMARY_QUESTION = (
    "Does today's valuation appropriately reflect the company's long-term intrinsic value and future expectations?"
)

CORE_QUESTIONS = [
    "Is current valuation justified?",
    "What assumptions are priced in?",
    "What must happen to support current valuation?",
    "How much margin of safety remains if execution undershoots?",
]


def knowledge_pack(ticker: str | None = None) -> dict[str, Any]:
    pack: dict[str, Any] = {
        "analyst": "Valuation Analyst",
        "mission": MISSION,
        "primary_question": PRIMARY_QUESTION,
        "domains": list(KNOWLEDGE_DOMAINS),
        "core_questions": list(CORE_QUESTIONS),
        "never_answers": [
            "business-model storytelling",
            "management character judgements",
            "technical momentum calls",
        ],
    }
    # Soft-consume Academy Books V3 — institutional objects, not PDF text
    try:
        from academy.books.flags import flag_books_v3
        from academy.books.v3.production import analyst_base

        if flag_books_v3():
            pack["academy_institutional"] = analyst_base(
                "valuation",
                question="How should I interpret high ROIC and margin of safety?",
            )
    except Exception:
        pass
    try:
        from management_intelligence.flags import is_enabled as mii_enabled

        if mii_enabled():
            pack["management_intelligence"] = {
                "enabled": True,
                "rule": "Management quality premium / capital allocation quality from MII only",
            }
            if ticker:
                from management_intelligence.production import soft_slice_for_analyst as mii_slice

                pack["management_intelligence"].update(
                    (mii_slice(ticker, analyst="valuation") or {}).get("management_intelligence") or {}
                )
    except Exception:
        pass
    try:
        from peer_intelligence.flags import is_enabled as pil_enabled

        if pil_enabled() and ticker:
            from peer_intelligence.production import soft_slice_for_analyst as pil_slice

            pack["peer_intelligence"] = (pil_slice(ticker, analyst="valuation") or {}).get(
                "peer_intelligence"
            ) or {"enabled": True}
    except Exception:
        pass
    try:
        from filing_intelligence.flags import is_enabled as fil_enabled

        if fil_enabled() and ticker:
            from filing_intelligence.production import soft_slice_for_analyst as fil_slice

            pack["filing_intelligence"] = (fil_slice(ticker, analyst="valuation") or {}).get(
                "filing_intelligence"
            ) or {"enabled": True}
    except Exception:
        pass
    try:
        from accounting_intelligence.flags import is_enabled as aci_enabled

        if aci_enabled():
            pack["accounting_intelligence"] = {
                "enabled": True,
                "rule": "Adjusted earnings quality and cash-backed valuation inputs from ACI only",
            }
            if ticker:
                from accounting_intelligence.production import soft_slice_for_analyst as aci_slice

                pack["accounting_intelligence"].update(
                    (aci_slice(ticker, analyst="valuation") or {}).get("accounting_intelligence") or {}
                )
    except Exception:
        pass
    return pack
