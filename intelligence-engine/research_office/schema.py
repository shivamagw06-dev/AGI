"""Institutional Research Office schemas — knowledge-only publications."""

from __future__ import annotations

from typing import Any

RO_VERSION = "research-office-v1.0.0"
PROGRAMME = "AGIB v2.2 – Institutional Research Office"
MODULE_CODE = "IROFFICE"

FORBIDDEN_CLAIMS: tuple[str, ...] = (
    "buy",
    "sell",
    "target price",
    "portfolio action",
    "overweight",
    "underweight",
    "accumulate",
    "reduce position",
)

PUBLICATION_TYPES: tuple[str, ...] = (
    "market_morning_brief",
    "macro_intelligence_brief",
    "government_intelligence_brief",
    "sector_intelligence_report",
    "industry_intelligence_report",
    "corporate_events_report",
    "alternative_data_report",
    "market_expectations_report",
    "company_research_note",
)

WATCHLIST_TYPES: tuple[str, ...] = (
    "research",
    "valuation",
    "corporate_events",
    "macro",
    "government",
    "risk",
    "alternative_data",
    "expectation",
)

FREEZE_LOCKS: dict[str, Any] = {
    "phases_1_7": True,
    "knowledge_factory": True,
    "ask_pipeline": True,
    "institutional_scheduler": True,
    "governance": True,
    "committees": True,
    "evidence_factory": True,
    "decision_quality": True,
    "continuous_adaptive_learning": True,
    "soft_wire_only": True,
    "knowledge_only": True,
    "no_recommendations": True,
    "no_new_reasoning": True,
}
