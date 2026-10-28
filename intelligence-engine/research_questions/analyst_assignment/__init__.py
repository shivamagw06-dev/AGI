"""Assign exactly one analyst owner per research question."""

from __future__ import annotations

from typing import Any

TYPE_OWNER: dict[str, str] = {
    "Verification": "Business",
    "Contradiction": "Risk",
    "Historical": "Valuation",
    "Peer": "Sector",
    "Macro": "Macro",
    "Accounting": "Accounting",
    "Business": "Business",
    "Financial": "Financial",
    "Management": "Management",
    "Valuation": "Valuation",
    "Portfolio": "Portfolio",
    "Forecast": "Forecast",
    "Risk": "Risk",
}

# Keyword overrides for more precise ownership
_KEYWORD_OWNER: tuple[tuple[str, str], ...] = (
    ("casa", "Business"),
    ("funding", "Business"),
    ("deposit", "Business"),
    ("credit cost", "Financial"),
    ("cash conversion", "Financial"),
    ("roic", "Financial"),
    ("gnpa", "Financial"),
    ("margin of safety", "Valuation"),
    ("percentile", "Valuation"),
    ("premium", "Valuation"),
    ("multiple", "Valuation"),
    ("conference call", "Management"),
    ("management", "Management"),
    ("portfolio", "Portfolio"),
    ("position size", "Portfolio"),
    ("macro", "Macro"),
    ("rate hik", "Macro"),
    ("accounting", "Accounting"),
)


def owner_for_question(question_type: str, question_text: str = "") -> str:
    lower = (question_text or "").lower()
    for kw, owner in _KEYWORD_OWNER:
        if kw in lower:
            return owner
    return TYPE_OWNER.get(question_type, "Business")


def assign_owners(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for q in questions:
        owner = owner_for_question(str(q.get("type") or ""), str(q.get("question") or ""))
        out.append({**q, "analyst_owner": owner})
    return out
