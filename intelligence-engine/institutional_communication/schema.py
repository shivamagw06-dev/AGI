"""ICE — Institutional Communication Engine schemas."""

from __future__ import annotations

from typing import Any

ICE_VERSION = "institutional-communication-v1.0.0"
PROGRAMME = "AGIB v3.4 – Institutional Answer Excellence · Track D Communication"
MODULE_CODE = "ICE"

FREEZE_LOCKS: dict[str, Any] = {
    "knowledge_factory": True,
    "governance_internals": True,
    "committees": True,
    "planner": True,
    "reasoning_frozen": True,
    "no_new_intelligence_domains": True,
    "soft_wire_only": True,
    "deterministic_renderer_only": True,
    "no_llm_narrative": True,
    "no_free_form_editorial": True,
}

TEMPLATES: tuple[str, ...] = (
    "educational",
    "comparison",
    "company_analysis",
    "industry_analysis",
    "macro_analysis",
    "government_analysis",
    "historical_replay",
    "portfolio_review",
    "research_note",
    "investment_committee_brief",
)

MANDATORY_SECTIONS: tuple[str, ...] = (
    "executive_summary",
    "evidence",
    "framework_used",
    "analysis",
    "risks",
    "confidence",
    "sources",
)

REPLAY_EXTRA_SECTIONS: tuple[str, ...] = (
    "historical_context",
    "replay_timestamp",
    "available_evidence",
    "future_leakage_check",
)

# Phrases that mark banned generic / ChatGPT-like filler in rendered output
GENERIC_MARKERS: tuple[str, ...] = (
    "business strength rated c",
    "valuation question blocked from unsupported narrative",
    "the company continues to show",
    "as an ai",
    "in conclusion, it is important",
    "delve into",
    "landscape is evolving",
)
