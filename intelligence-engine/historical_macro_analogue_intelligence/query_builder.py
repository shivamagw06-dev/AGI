"""Analogue query builder — natural language / filters → structured search."""

from __future__ import annotations

import re
from typing import Any

_TIGHTENING = re.compile(r"tighten|hiking|rate hike|inflation shock|2022", re.I)
_EASING = re.compile(r"easing|rate cut|disinflation|accommodative", re.I)
_TAPER = re.compile(r"2013|taper|external stress|rupee", re.I)
_COVID = re.compile(r"covid|pandemic|2020", re.I)
_GFC = re.compile(r"\b2008\b|gfc|global financial", re.I)


def detect_target_period(question: str | None, *, explicit: str | None = None) -> str | None:
    if explicit:
        return str(explicit)
    if not question:
        return None
    if _GFC.search(question):
        return "2008"
    if _TAPER.search(question):
        return "2013"
    if _COVID.search(question):
        return "2020"
    if _TIGHTENING.search(question) and "2022" in question:
        return "2022"
    years = re.findall(r"\b((?:19|20)\d{2})\b", question or "")
    if years:
        return years[0]
    return None


def detect_situation(question: str | None) -> str | None:
    if not question:
        return None
    if _EASING.search(question):
        return "easing"
    if _TIGHTENING.search(question):
        return "tightening"
    if _TAPER.search(question):
        return "external_stress"
    if _COVID.search(question):
        return "covid_shock"
    if _GFC.search(question):
        return "crisis"
    return "current_vs_history"


def build_search_query(
    *,
    country: str = "India",
    question: str | None = None,
    target_period: str | None = None,
    top_k: int = 5,
    min_score: float = 0.0,
) -> dict[str, Any]:
    period = detect_target_period(question, explicit=target_period)
    return {
        "country": country,
        "question": question,
        "target_period": period,
        "situation": detect_situation(question),
        "top_k": top_k,
        "min_score": min_score,
        "providers_queried": [],
    }
