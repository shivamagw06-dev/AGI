"""Deterministic Ask AGI routing before company identity enforcement."""

from __future__ import annotations

import re

HOUSE_RESEARCH = "HOUSE_RESEARCH"
THEMATIC_RESEARCH = "THEMATIC_RESEARCH"
COMPANY_RESEARCH = "COMPANY_RESEARCH"

_LISTED_AGI_COMPANY_RE = re.compile(r"\bagi\s+(?:greenpac|infra)\b", re.I)
_HOUSE_RESEARCH_RE = re.compile(
    r"\b(?:global investment monitor|agi(?:['’]s)?\s+(?:house\s+view|research|view|views|"
    r"thinks?|expects?|says?|wrote)|(?:what|how)\s+(?:does|did|is|was)\s+agi\s+"
    r"(?:think|view|say|expect|write)|according\s+to\s+agi)\b",
    re.I,
)
_THEMATIC_RESEARCH_RE = re.compile(
    r"\b(?:ai\s+(?:spending|investment|capex|infrastructure)|hyperscaler|"
    r"data[ -]?cent(?:er|re)|sector\s+rotation|sector\s+leadership|policy\s+shifts?|"
    r"market\s+rotation|beneficiary\s+sectors?|power\s+(?:names?|companies|demand)|"
    r"capital\s+spending)\b",
    re.I,
)


def classify_research_route(question: str) -> str:
    """Return the routing class needed by the company identity gate."""
    q = str(question or "").strip()
    if _LISTED_AGI_COMPANY_RE.search(q):
        return COMPANY_RESEARCH
    if _HOUSE_RESEARCH_RE.search(q):
        return HOUSE_RESEARCH
    if _THEMATIC_RESEARCH_RE.search(q):
        return THEMATIC_RESEARCH
    return COMPANY_RESEARCH


def company_required(question: str) -> bool:
    return classify_research_route(question) == COMPANY_RESEARCH


__all__ = [
    "COMPANY_RESEARCH",
    "HOUSE_RESEARCH",
    "THEMATIC_RESEARCH",
    "classify_research_route",
    "company_required",
]
