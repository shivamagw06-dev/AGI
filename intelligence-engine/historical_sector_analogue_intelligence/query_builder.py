"""Analogue query builder — natural language / filters → structured sector search."""

from __future__ import annotations

import re
from typing import Any

from historical_sector_analogue_intelligence.schema import SUPPORTED_SECTORS

_SECTOR_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bbank(ing|s)?\b|credit cycle|npa|nim\b", re.I), "Banking"),
    (re.compile(r"\bit\b|infosys|tcs|technology spending|usd/?inr", re.I), "IT Services"),
    (re.compile(r"fmcg|rural demand|consumer staples", re.I), "FMCG"),
    (re.compile(r"\bauto\b|automobile|vehicle demand|maruti", re.I), "Auto"),
    (re.compile(r"capital goods|order book|capex|infrastructure spending|l&t", re.I), "Capital Goods"),
    (re.compile(r"pharma|pharmaceutical|drug pricing", re.I), "Pharma"),
]

_GFC = re.compile(r"\b2008\b|gfc|global financial", re.I)
_TAPER = re.compile(r"\b2013\b|taper", re.I)
_CREDIT = re.compile(r"\b2017\b|credit cycle|demonet", re.I)
_COVID = re.compile(r"covid|pandemic|\b2020\b", re.I)
_TIGHTENING = re.compile(r"tighten|hiking|inflation shock|\b2022\b", re.I)


def detect_sector(question: str | None, *, explicit: str | None = None) -> str | None:
    if explicit:
        for s in SUPPORTED_SECTORS:
            if explicit.lower() == s.lower() or explicit.lower() in s.lower():
                return s
        return explicit
    if not question:
        return None
    for pattern, sector in _SECTOR_PATTERNS:
        if pattern.search(question):
            return sector
    return None


def detect_target_period(question: str | None, *, explicit: str | None = None) -> str | None:
    if explicit:
        return str(explicit)
    if not question:
        return None
    if _GFC.search(question):
        return "2008"
    if _TAPER.search(question):
        return "2013"
    if _CREDIT.search(question):
        return "2017"
    if _COVID.search(question):
        return "2020"
    if _TIGHTENING.search(question) and "2022" in question:
        return "2022"
    years = re.findall(r"\b((?:19|20)\d{2})\b", question or "")
    if years:
        return years[0]
    return None


def build_search_query(
    *,
    sector: str | None = None,
    question: str | None = None,
    target_period: str | None = None,
    top_k: int = 5,
    min_score: float = 0.0,
) -> dict[str, Any]:
    resolved = detect_sector(question, explicit=sector) or "Banking"
    period = detect_target_period(question, explicit=target_period)
    return {
        "sector": resolved,
        "question": question,
        "target_period": period,
        "top_k": top_k,
        "min_score": min_score,
        "providers_queried": [],
    }
