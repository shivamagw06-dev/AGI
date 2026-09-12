"""Document type detection from title/text/metadata."""

from __future__ import annotations

from typing import Any

from filing_intelligence.schema import DOC_TYPES

_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("annual_report", ("annual report", "integrated report", "form 10-k")),
    # presentations before quarterly — titles often include Q1FY…
    ("investor_presentation", ("earnings presentation", "investor presentation", "earnings deck")),
    ("transcript", ("conference call", "earnings call", "transcript")),
    ("press_release", ("press release",)),
    ("quarterly_results", ("quarterly results", "results for quarter", "q1fy", "q2fy", "q3fy", "q4fy")),
    ("shareholding_filing", ("shareholding pattern", "beneficial ownership")),
    ("dividend_announcement", ("dividend", "interim dividend")),
    ("acquisition_filing", ("acquisition", "scheme of amalgamation", "merger")),
    ("capital_raise", ("qip", "fpo", "rights issue", "capital raise")),
    ("governance_report", ("corporate governance", "board report")),
    ("sustainability_report", ("sustainability", "brsr", "esg report")),
    ("board_meeting", ("board meeting",)),
    ("regulatory_filing", ("sebi", "rbi circular disclosure", "exchange filing")),
    ("presentation_deck", ("presentation", "deck")),
]


def detect_doc_type(title: str = "", text: str = "", hint: str | None = None) -> dict[str, Any]:
    if hint and hint in DOC_TYPES:
        return {"doc_type": hint, "confidence": 1.0, "method": "hint"}
    blob = f"{title} {text}".lower()
    for doc_type, keys in _RULES:
        if any(k in blob for k in keys):
            return {"doc_type": doc_type, "confidence": 0.85, "method": "keyword"}
    return {"doc_type": "regulatory_filing", "confidence": 0.4, "method": "default"}
