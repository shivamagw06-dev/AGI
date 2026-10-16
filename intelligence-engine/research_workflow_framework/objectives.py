"""Decision objective resolution — what is the user trying to decide?"""

from __future__ import annotations

import re
from typing import Any

DECISION_OBJECTIVES: tuple[str, ...] = (
    "Evaluate Investment Opportunity",
    "Understand Company",
    "Understand Valuation",
    "Understand Business Quality",
    "Understand Financial Strength",
    "Understand Management",
    "Understand Risk",
    "Understand Earnings",
    "Understand Competitive Position",
    "Compare Companies",
    "Compare Sectors",
    "Understand Macro Impact",
    "Review Portfolio",
    "Review Watchlist",
    "Review Thesis",
    "Monitor Existing Investment",
    "Understand Market",
    "Learn Investment Concepts",
)

_CUE_OBJECTIVES: tuple[tuple[str, str], ...] = (
    (r"\bshould i buy\b|\bworth investing\b|\binvestment case\b", "Evaluate Investment Opportunity"),
    (r"\bexpensive\b|\bcheap\b|\bovervalued\b|\bundervalued\b|\bvaluation\b", "Understand Valuation"),
    (r"\bmoat\b|\bbusiness quality\b|\bfranchise\b", "Understand Business Quality"),
    (r"\bearnings\b|\bresults\b|\bquarter\b", "Understand Earnings"),
    (r"\bcompare\b|\b vs \b|\bversus\b|\bpeer\b", "Compare Companies"),
    (r"\bportfolio\b|\bholdings\b|\ballocation\b", "Review Portfolio"),
    (r"\bwatchlist\b", "Review Watchlist"),
    (r"\bthesis\b|\bwhat changed\b", "Review Thesis"),
    (r"\bmarket\b|\bnifty\b|\bsensex\b", "Understand Market"),
    (r"\bmacro\b|\brbi\b|\binflation\b|\brate\b", "Understand Macro Impact"),
    (r"\brisk\b|\bdownside\b", "Understand Risk"),
    (r"\bexplain\b|\bwhat is\b|\bhow does\b|\bdefine\b", "Learn Investment Concepts"),
)

_IRL_OBJECTIVES: dict[str, str] = {
    "Analyse": "Evaluate Investment Opportunity",
    "Valuation": "Understand Valuation",
    "Compare": "Compare Companies",
    "Portfolio": "Review Portfolio",
    "Risk": "Understand Risk",
    "Explain": "Learn Investment Concepts",
    "Education": "Learn Investment Concepts",
    "Industry": "Compare Sectors",
    "Macro": "Understand Macro Impact",
    "Documents": "Understand Financial Strength",
    "HistoricalReplay": "Review Thesis",
    "CrossDomain": "Evaluate Investment Opportunity",
    "Unknown": "Understand Company",
}


def resolve_decision_objective(
    question: str,
    *,
    irl_intent: str | None = None,
    aic_intent: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Map user question to a single decision objective."""
    q = (question or "").strip()
    low = q.lower()

    for pattern, objective in _CUE_OBJECTIVES:
        if re.search(pattern, low):
            return {"objective": objective, "source": "question_cue", "question": q}

    if isinstance(aic_intent, dict) and aic_intent.get("real_intent"):
        primary = aic_intent.get("primary_intent") or ""
        mapped = _map_aic_primary(primary)
        if mapped:
            return {
                "objective": mapped,
                "source": "ask_intelligence_constitution",
                "real_intent": aic_intent.get("real_intent"),
                "question": q,
            }

    intent = (irl_intent or "").strip()
    if intent and intent in _IRL_OBJECTIVES:
        return {"objective": _IRL_OBJECTIVES[intent], "source": "irl_intent", "question": q}

    return {"objective": "Understand Company", "source": "default", "question": q}


def _map_aic_primary(primary: str) -> str | None:
    m = {
        "INVESTMENT_ASSESSMENT": "Evaluate Investment Opportunity",
        "VALUATION": "Understand Valuation",
        "BUSINESS_QUALITY": "Understand Business Quality",
        "FINANCIAL_ANALYSIS": "Understand Financial Strength",
        "EARNINGS_ANALYSIS": "Understand Earnings",
        "RISK_ANALYSIS": "Understand Risk",
        "PEER_COMPARISON": "Compare Companies",
        "PORTFOLIO_ANALYSIS": "Review Portfolio",
        "MACRO_ANALYSIS": "Understand Macro Impact",
        "SECTOR_ANALYSIS": "Compare Sectors",
        "MARKET_OVERVIEW": "Understand Market",
        "THESIS_CHANGE": "Review Thesis",
        "EDUCATION": "Learn Investment Concepts",
    }
    return m.get(primary)
