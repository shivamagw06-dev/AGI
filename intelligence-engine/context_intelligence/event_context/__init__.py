"""Detect catalysts / events surrounding the question."""

from __future__ import annotations

import re
from typing import Any

_EVENTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(earnings|results?\s+day|quarterly\s+results?)\b", re.I), "Earnings"),
    (re.compile(r"\b(union\s+budget|budget\s+day)\b", re.I), "Budget"),
    (re.compile(r"\b(election|polls?)\b", re.I), "Election"),
    (re.compile(r"\b(fed\s+meeting|fomc)\b", re.I), "Fed Meeting"),
    (re.compile(r"\b(rbi\s+meeting|mpc|policy\s+meeting)\b", re.I), "RBI Meeting"),
    (re.compile(r"\b(acquisition|acquire[ds]?)\b", re.I), "Acquisition"),
    (re.compile(r"\b(guidance|outlook\s+cut|outlook\s+raise)\b", re.I), "Guidance"),
    (re.compile(r"\b(product\s+launch|launch(?:es|ed)?)\b", re.I), "Product Launch"),
    (re.compile(r"\b(merger|amalgamation)\b", re.I), "Merger"),
    (re.compile(r"\b(management\s+change|ceo\s+change|new\s+ceo)\b", re.I), "Management Change"),
    (re.compile(r"\b(rate\s+cuts?|rate\s+hikes?)\b", re.I), "Rate Decision"),
]


def detect_event_context(question: str) -> dict[str, Any]:
    text = question or ""
    hits = [name for pat, name in _EVENTS if pat.search(text)]
    return {
        "events": hits,
        "primary_event": hits[0] if hits else None,
        "catalyst_context": hits,
        "required": bool(hits),
        "confidence": 0.96 if hits else 0.75,
    }
