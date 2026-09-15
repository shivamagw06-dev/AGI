"""Analogue query builder — natural language / filters → structured market search."""

from __future__ import annotations

import re
from typing import Any

from historical_market_analogue_intelligence.schema import SUPPORTED_MARKETS

_MARKET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bglobal\b|s&p|nasdaq|world|us market", re.I), "Global"),
    (re.compile(r"\bindia\b|nifty|sensex|in market|domestic", re.I), "India"),
]

_GFC = re.compile(r"\b2008\b|gfc|global financial", re.I)
_TAPER = re.compile(r"\b2013\b|taper", re.I)
_DEMON = re.compile(r"\b2016\b|demonet", re.I)
_COVID = re.compile(r"covid|pandemic|\b2020\b", re.I)
_RECOVERY = re.compile(r"\b2021\b|liquidity rally|recovery", re.I)
_INFLATION = re.compile(r"tighten|inflation shock|\b2022\b", re.I)
_BULL = re.compile(r"\b2003\b|bull market", re.I)
_DOTCOM = re.compile(r"\b2000\b|dot-?com", re.I)


def detect_market(question: str | None, *, explicit: str | None = None) -> str | None:
    if explicit:
        for s in SUPPORTED_MARKETS:
            if explicit.lower() == s.lower() or explicit.lower() in s.lower():
                return s
        from historical_market_analogue_intelligence.regimes import normalize_market

        return normalize_market(explicit)
    if not question:
        return None
    for pattern, market in _MARKET_PATTERNS:
        if pattern.search(question):
            return market
    return "India"


def detect_target_period(question: str | None, *, explicit: str | None = None) -> str | None:
    if explicit:
        return str(explicit)
    if not question:
        return None
    if _DOTCOM.search(question):
        return "2000"
    if _BULL.search(question) and "2003" in question:
        return "2003"
    if _GFC.search(question):
        return "2008"
    if _TAPER.search(question):
        return "2013"
    if _DEMON.search(question):
        return "2016"
    if _COVID.search(question):
        return "2020"
    if _RECOVERY.search(question) and "2021" in (question or ""):
        return "2021"
    if _INFLATION.search(question) and "2022" in (question or ""):
        return "2022"
    years = re.findall(r"\b((?:19|20)\d{2})\b", question or "")
    if years:
        return years[0]
    return None


def build_search_query(
    *,
    market: str | None = None,
    question: str | None = None,
    target_period: str | None = None,
    top_k: int = 5,
    min_score: float = 0.0,
) -> dict[str, Any]:
    resolved = detect_market(question, explicit=market) or "India"
    period = detect_target_period(question, explicit=target_period)
    return {
        "market": resolved,
        "question": question,
        "target_period": period,
        "top_k": top_k,
        "min_score": min_score,
        "providers_queried": [],
    }
