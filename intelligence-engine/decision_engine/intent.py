"""Detect multi-layer investment decision questions — soft-wire only."""

from __future__ import annotations

import re

_BUY_RE = re.compile(
    r"(?i)\b("
    r"should\s+i\s+(buy|sell|hold|invest|accumulate)|"
    r"(buy|sell|hold|accumulate|invest\s+in)\b|"
    r"investment\s+(case|decision|recommendation)|"
    r"worth\s+(buying|investing)|"
    r"add\s+to\s+(portfolio|position)|"
    r"core\s+holding"
    r")\b"
)


def is_investment_decision_question(query: str = "", *, leo_pkg: dict | None = None, irp: dict | None = None) -> bool:
    q = str(query or "").strip()
    if _BUY_RE.search(q):
        return True
    leo = leo_pkg if isinstance(leo_pkg, dict) else {}
    if leo.get("is_investment") or str(leo.get("intent") or "").lower() in {
        "investment_recommendation",
        "buy_sell",
    }:
        return True
    irp = irp if isinstance(irp, dict) else {}
    intent = str(irp.get("intent") or "").lower()
    if intent in {"company_research", "investment_thesis", "valuation"} and _BUY_RE.search(q):
        return True
    return bool(intent == "investment_thesis")
