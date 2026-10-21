"""Source authority scoring — Tier 1–6 institutional priority."""

from __future__ import annotations

AUTHORITY_SCORES: dict[str, int] = {
    "annual_report": 10,
    "quarterly_report": 10,
    "exchange_filing": 10,
    "sec_filing": 10,
    "nse_bse_filing": 10,
    "government": 9,
    "rbi": 9,
    "sebi": 9,
    "conference_call": 9,
    "transcript": 9,
    "investor_presentation": 8,
    "reuters": 8,
    "bloomberg": 8,
    "world_bank": 8,
    "imf": 8,
    "fred": 8,
    "oecd": 8,
    "cnbc": 7,
    "moneycontrol": 7,
    "economic_times": 7,
    "business_standard": 7,
    "mint": 7,
    "industry_report": 6,
    "trade_association": 6,
    "research_publication": 6,
    "wikipedia": 4,
    "general_web": 3,
    "unknown_blog": 2,
    "unknown": 2,
}

TIER_BY_SOURCE: dict[str, int] = {
    "company_ir": 1,
    "annual_report": 1,
    "quarterly_report": 1,
    "investor_presentation": 1,
    "exchange_filing": 1,
    "nse": 2,
    "bse": 2,
    "sebi": 2,
    "rbi": 2,
    "government": 2,
    "pib": 2,
    "mca": 2,
    "world_bank": 3,
    "imf": 3,
    "oecd": 3,
    "fred": 3,
    "reuters": 4,
    "bloomberg": 4,
    "cnbc": 4,
    "moneycontrol": 4,
    "economic_times": 4,
    "business_standard": 4,
    "mint": 4,
    "industry_report": 5,
    "trade_association": 5,
    "research_publication": 5,
    "general_web": 6,
    "unknown": 6,
}


def authority_score(document_type: str | None = None, source: str | None = None) -> int:
    for key in (document_type, source):
        if key and key.lower() in AUTHORITY_SCORES:
            return AUTHORITY_SCORES[key.lower()]
    return AUTHORITY_SCORES["unknown"]


def source_tier(document_type: str | None = None, source: str | None = None) -> int:
    for key in (document_type, source):
        if key and key.lower() in TIER_BY_SOURCE:
            return TIER_BY_SOURCE[key.lower()]
    return 6


def normalize_authority(score: int) -> float:
    return max(0.0, min(1.0, float(score) / 10.0))
