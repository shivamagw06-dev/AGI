"""Institutional response templates — intent-aware section patterns."""

from __future__ import annotations

from typing import Any

# Each template defines section order and investor-facing purpose
RESPONSE_TEMPLATES: dict[str, dict[str, Any]] = {
    "investment_assessment": {
        "label": "Investment Assessment",
        "sections": (
            "executive_summary",
            "investment_debate",
            "supporting_evidence",
            "key_uncertainties",
            "research_conclusion",
            "questions_before_you_decide",
        ),
        "triggers": ("should i invest", "investment case", "should i buy", "worth investing"),
    },
    "earnings_review": {
        "label": "Earnings Review",
        "sections": (
            "executive_summary",
            "what_changed",
            "what_didnt_change",
            "market_implications",
            "supporting_evidence",
            "monitoring",
            "research_conclusion",
        ),
        "triggers": ("earnings", "what changed", "quarterly results", "latest results"),
    },
    "valuation": {
        "label": "Valuation",
        "sections": (
            "executive_summary",
            "current_expectations",
            "historical_context",
            "supporting_evidence",
            "key_uncertainties",
            "research_conclusion",
        ),
        "triggers": ("valued at", "fairly valued", "valuation", "premium", "discount", "expensive", "cheap"),
    },
    "peer_comparison": {
        "label": "Peer Comparison",
        "sections": (
            "executive_summary",
            "business_comparison",
            "financial_comparison",
            "competitive_position",
            "supporting_evidence",
            "research_conclusion",
        ),
        "triggers": ("compare", " vs ", " versus ", "better than", "relative to"),
    },
    "risk_review": {
        "label": "Risk Review",
        "sections": (
            "executive_summary",
            "primary_risks",
            "supporting_evidence",
            "probability",
            "monitoring",
            "research_conclusion",
        ),
        "triggers": ("risk", "downside", "invalidate", "what could go wrong", "key risks"),
    },
    "narrative_default": {
        "label": "Institutional Narrative",
        "sections": (
            "executive_summary",
            "what_matters_most",
            "investment_debate",
            "supporting_evidence",
            "key_uncertainties",
            "research_conclusion",
            "questions_before_you_decide",
        ),
        "triggers": (),
    },
}

DEFAULT_TEMPLATE = "narrative_default"


def resolve_template(query: str, *, category: str | None = None) -> str:
    """Pick response template from query text and optional benchmark category."""
    category_map = {
        "investment_assessment": "investment_assessment",
        "valuation": "valuation",
        "earnings_analysis": "earnings_review",
        "peer_comparison": "peer_comparison",
        "risk_analysis": "risk_review",
        "thesis_change": "risk_review",
    }
    if category and category in category_map:
        return category_map[category]

    q = (query or "").lower()
    for template_id, spec in RESPONSE_TEMPLATES.items():
        if template_id == DEFAULT_TEMPLATE:
            continue
        if any(t in q for t in spec.get("triggers") or ()):
            return template_id
    return DEFAULT_TEMPLATE


def template_sections(template_id: str) -> tuple[str, ...]:
    spec = RESPONSE_TEMPLATES.get(template_id) or RESPONSE_TEMPLATES[DEFAULT_TEMPLATE]
    return tuple(spec["sections"])
