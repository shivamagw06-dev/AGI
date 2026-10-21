"""Detect contradiction / conflicting-signal questions."""

from __future__ import annotations

import re

_CONFLICT_MARKERS = re.compile(
    r"\b("
    r"but|however|despite|whereas|while|although|yet|"
    r"contradict|conflict|tension|mismatch|diverge|"
    r"on\s+the\s+other\s+hand|even\s+though"
    r")\b",
    re.I,
)

_CONTRADICTION_ASK = re.compile(
    r"\b("
    r"which\s+signal|"
    r"more\s+important|"
    r"explain\s+the\s+contradiction|"
    r"how\s+should\s+this\s+be\s+interpreted|"
    r"how\s+to\s+interpret|"
    r"what\s+does\s+this\s+mean|"
    r"reconcile|"
    r"conflicting|"
    r"contradiction"
    r")\b",
    re.I,
)

# Fact-pair patterns that commonly conflict in finance questions.
_PAIR_HINTS = (
    re.compile(r"\b(profit|earnings|net\s+profit|pat)\b.*\b(nim|net\s+interest\s+margin|margin)\b", re.I | re.S),
    re.compile(r"\b(nim|net\s+interest\s+margin|margin)\b.*\b(profit|earnings|net\s+profit|pat)\b", re.I | re.S),
    re.compile(r"\b(revenue|sales)\b.*\b(free\s+cash\s+flow|fcf|cash\s+flow)\b", re.I | re.S),
    re.compile(r"\b(free\s+cash\s+flow|fcf|cash\s+flow)\b.*\b(revenue|sales)\b", re.I | re.S),
    re.compile(r"\b(management|guidance|commentary|says?|claimed)\b.*\b(sales|revenue|demand)\b", re.I | re.S),
    re.compile(r"\b(sales|revenue)\b.*\b(management|guidance|commentary|says?|claimed)\b", re.I | re.S),
)


def is_contradiction_query(query: str | None) -> bool:
    text = str(query or "").strip()
    if not text:
        return False
    if _CONTRADICTION_ASK.search(text) and _CONFLICT_MARKERS.search(text):
        return True
    if _CONFLICT_MARKERS.search(text) and any(p.search(text) for p in _PAIR_HINTS):
        return True
    if re.search(r"\bexplain\s+the\s+contradiction\b", text, re.I):
        return True
    return False
