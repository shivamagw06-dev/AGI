"""P6 Autonomous Research Office — schema (not an intelligence engine)."""

from __future__ import annotations

ENGINE_CODE = "autonomous_research"
ENGINE_NAME = "Autonomous Research Office"
VERSION = "p6-autonomous-research-office-v1.0.0"
PROGRAMME = "AGIB_PHASE6_AUTONOMOUS_RESEARCH_OFFICE"
WORKSTREAM_ID = "P6"
MILESTONE = "phase_6_aro"

RECOMMENDATION_POLICY = "autonomous_research_drafts_only_no_buy_sell"

CAPABILITIES = (
    "research_planner",
    "research_generator",
    "coverage_manager",
    "watchlist_manager",
    "theme_intelligence",
    "evidence_monitor",
    "portfolio_review",
    "publication_pipeline",
    "institutional_qa",
    "learning_feedback",
)

RESEARCH_TYPES = (
    "company_update",
    "earnings_preview",
    "earnings_review",
    "sector_note",
    "theme_note",
    "macro_brief",
    "event_analysis",
    "risk_update",
)

WATCHLIST_BUCKETS = (
    "high_priority",
    "medium_priority",
    "low_priority",
    "event_driven",
    "macro_sensitive",
    "portfolio_critical",
)

PUBLICATION_TYPES = (
    "morning_brief",
    "evening_brief",
    "research_note",
    "sector_report",
    "theme_report",
    "weekly_review",
    "monthly_review",
)

THEME_CATALOG = (
    "AI",
    "Power",
    "Defence",
    "Manufacturing",
    "Banking",
    "Infrastructure",
    "Renewable Energy",
    "Cement",
    "Pharma",
    "Auto",
)

QA_CHECKS = (
    "evidence_completeness",
    "company_memory_version",
    "knowledge_delta_version",
    "graph_consistency",
    "citation_availability",
    "deterministic_replay",
    "confidence_threshold",
)
