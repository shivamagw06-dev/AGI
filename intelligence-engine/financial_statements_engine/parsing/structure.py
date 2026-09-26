"""Structure detection — statement sections."""

from __future__ import annotations

from typing import Any

SECTION_HINTS = {
    "income_statement": ("revenue", "income", "profit", "ebit", "pat", "expense", "tax"),
    "balance_sheet": ("asset", "liabilit", "equity", "cash", "inventory", "receivable"),
    "cash_flow": ("operating", "investing", "financing", "cash_flow", "cashflow"),
    "segment_statement": ("segment",),
    "share_capital": ("share_capital", "face_value", "shares"),
    "eps": ("eps", "earnings per"),
    "notes": ("note", "footnote"),
}


def detect_structure(fields: dict[str, Any], sections_hint: list[str] | None = None) -> dict[str, Any]:
    if sections_hint:
        sections = list(sections_hint)
    else:
        blob = " ".join(str(k).lower() for k in (fields or {}))
        sections = []
        for section, hints in SECTION_HINTS.items():
            if any(h in blob for h in hints):
                sections.append(section)
        if not sections:
            sections = ["unknown"]
    return {
        "sections": sections,
        "section_boundaries_preserved": True,
        "layer": "structure_detection",
    }
