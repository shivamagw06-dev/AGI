"""Deterministic template structures — section order only."""

from __future__ import annotations

from institutional_communication.schema import MANDATORY_SECTIONS, REPLAY_EXTRA_SECTIONS

BASE = list(MANDATORY_SECTIONS)

TEMPLATES: dict[str, dict] = {
    "educational": {
        "id": "educational",
        "title": "Educational Explanation",
        "sections": BASE,
        "lead": "framework_first",
    },
    "comparison": {
        "id": "comparison",
        "title": "Peer Comparison",
        "sections": BASE,
        "lead": "evidence_first",
    },
    "company_analysis": {
        "id": "company_analysis",
        "title": "Company Analysis",
        "sections": BASE,
        "lead": "evidence_first",
    },
    "industry_analysis": {
        "id": "industry_analysis",
        "title": "Industry Analysis",
        "sections": BASE,
        "lead": "framework_first",
    },
    "macro_analysis": {
        "id": "macro_analysis",
        "title": "Macro Analysis",
        "sections": BASE,
        "lead": "framework_first",
    },
    "government_analysis": {
        "id": "government_analysis",
        "title": "Government / Policy Analysis",
        "sections": BASE,
        "lead": "framework_first",
    },
    "historical_replay": {
        "id": "historical_replay",
        "title": "Historical Replay",
        "sections": [
            "executive_summary",
            "historical_context",
            "replay_timestamp",
            "available_evidence",
            "future_leakage_check",
            "evidence",
            "framework_used",
            "analysis",
            "risks",
            "confidence",
            "sources",
        ],
        "lead": "replay_first",
        "extra": list(REPLAY_EXTRA_SECTIONS),
    },
    "portfolio_review": {
        "id": "portfolio_review",
        "title": "Portfolio Review",
        "sections": BASE,
        "lead": "risk_first",
    },
    "research_note": {
        "id": "research_note",
        "title": "Research Note",
        "sections": BASE,
        "lead": "evidence_first",
    },
    "investment_committee_brief": {
        "id": "investment_committee_brief",
        "title": "Investment Committee Brief",
        "sections": BASE,
        "lead": "framework_first",
    },
}


def get_template(template_id: str) -> dict:
    return dict(TEMPLATES.get(template_id) or TEMPLATES["research_note"])
