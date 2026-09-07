"""Business Analyst knowledge catalog — institutional strategy frameworks (not engines)."""

from __future__ import annotations

from typing import Any

# Public institutional language only — never expose package/engine names.
KNOWLEDGE_DOMAINS: list[str] = [
    "Porter Five Forces",
    "Value Chain",
    "Competitive Advantage",
    "Blue Ocean Strategy",
    "Capital Cycle",
    "Network Effects",
    "Switching Costs",
    "Brand Strength",
    "Economies of Scale",
    "Pricing Power",
    "Customer Lifetime Value",
    "Customer Acquisition Cost",
    "Retention",
    "Operating Leverage",
    "Market Share",
    "Distribution",
    "Competitive Positioning",
    "Capital Allocation",
    "Innovation",
    "Technology Disruption",
]

MISSION = (
    "Determine whether this is a high-quality business capable of generating durable long-term value."
)

PRIMARY_QUESTION = "Would a long-term institutional investor want to own this business?"

CORE_QUESTIONS = [
    "Is this business improving?",
    "Why?",
    "Can competitors replicate it?",
    "How durable is its moat?",
    "Why do customers stay?",
    "How does it make money?",
    "What creates long-term value?",
]


def knowledge_pack(ticker: str | None = None) -> dict[str, Any]:
    pack: dict[str, Any] = {
        "analyst": "Business Analyst",
        "mission": MISSION,
        "primary_question": PRIMARY_QUESTION,
        "domains": list(KNOWLEDGE_DOMAINS),
        "core_questions": list(CORE_QUESTIONS),
        "never_answers": [
            "valuation attractiveness",
            "earnings multiple verdicts",
            "macro policy stance",
            "tape / momentum calls",
        ],
    }
    try:
        from academy.books.flags import flag_books_v3
        from academy.books.v3.production import analyst_base

        if flag_books_v3():
            pack["academy_institutional"] = analyst_base(
                "business",
                question="moat pricing power capital cycle network effects",
            )
    except Exception:
        pass
    try:
        from peer_intelligence.flags import is_enabled as pil_enabled

        if pil_enabled():
            pack["peer_intelligence"] = {
                "enabled": True,
                "rule": "Business conclusions must reference peer rank, history, or sector percentile before judgement",
                "soft_slice": "peer_intelligence.production.soft_slice_for_analyst(ticker, analyst='business')",
            }
            if ticker:
                from peer_intelligence.production import soft_slice_for_analyst as pil_slice

                pack["peer_intelligence"].update((pil_slice(ticker, analyst="business") or {}).get("peer_intelligence") or {})
    except Exception:
        pass
    try:
        from filing_intelligence.flags import is_enabled as fil_enabled

        if fil_enabled():
            pack["filing_intelligence"] = {
                "enabled": True,
                "rule": "Business-model evolution and management strategy must cite filing commentary when available",
                "soft_slice": "filing_intelligence.production.soft_slice_for_analyst(ticker, analyst='business')",
            }
            if ticker:
                from filing_intelligence.production import soft_slice_for_analyst as fil_slice

                pack["filing_intelligence"].update(
                    (fil_slice(ticker, analyst="business") or {}).get("filing_intelligence") or {}
                )
    except Exception:
        pass
    try:
        from management_intelligence.flags import is_enabled as mii_enabled

        if mii_enabled():
            pack["management_intelligence"] = {
                "enabled": True,
                "rule": "Leadership quality and competitive execution must use MII evidence, not vibes",
                "soft_slice": "management_intelligence.production.soft_slice_for_analyst(ticker, analyst='business')",
            }
            if ticker:
                from management_intelligence.production import soft_slice_for_analyst as mii_slice

                pack["management_intelligence"].update(
                    (mii_slice(ticker, analyst="business") or {}).get("management_intelligence") or {}
                )
    except Exception:
        pass
    try:
        from filing_diff.flags import is_enabled as fdi_enabled

        if fdi_enabled():
            pack["filing_diff"] = {
                "enabled": True,
                "rule": "Business what-changed must prefer FDI material changes over narrative drift",
            }
            if ticker:
                from filing_diff.production import soft_slice_for_analyst as fdi_slice

                pack["filing_diff"].update((fdi_slice(ticker, analyst="business") or {}).get("filing_diff") or {})
    except Exception:
        pass
    try:
        from accounting_intelligence.flags import is_enabled as aci_enabled

        if aci_enabled():
            pack["accounting_intelligence"] = {
                "enabled": True,
                "rule": "Business receives accounting quality summary only — not full forensic desk",
            }
            if ticker:
                from accounting_intelligence.production import soft_slice_for_analyst as aci_slice

                pack["accounting_intelligence"].update(
                    (aci_slice(ticker, analyst="business") or {}).get("accounting_intelligence") or {}
                )
    except Exception:
        pass
    return pack
