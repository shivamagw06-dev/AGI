"""Catalyst & Trigger Intelligence (CTI) — Sprint 9.3 contracts."""

from __future__ import annotations

from typing import Any

CTI_VERSION = "catalyst-trigger-intelligence-v1.0.0"
PROGRAMME = "AGI Phase 9 – Sprint 9.3 Catalyst & Trigger Intelligence"
PROGRAMME_SHORT = "CTI"
ARCHITECTURE_STATUS = "v1.0.0"

PRIMARY_QUESTION = "What events would make us change our view?"
INSTITUTIONAL_RULE = "We are Base Case unless X happens."

# Trigger lifecycle
TRIGGER_STATES: tuple[str, ...] = (
    "Scheduled",
    "Watching",
    "Triggered",
    "Confirmed",
    "Applied",
    "Archived",
)

CATALYST_CATEGORIES: tuple[str, ...] = (
    "company",
    "sector",
    "macro",
    "market",
)

SCENARIO_IMPACTS: tuple[str, ...] = (
    "strengthens_bull",
    "weakens_bull",
    "strengthens_base",
    "weakens_base",
    "invalidates_base",
    "strengthens_bear",
    "weakens_bear",
    "neutral",
)

PRIORITIES: tuple[str, ...] = ("Critical", "High", "Medium", "Low")

FREEZE_LOCKS: dict[str, Any] = {
    "does_not_forecast": True,
    "does_not_auto_rewrite_thesis": True,
    "does_not_auto_change_governance": True,
    "scenario_impact_assessment_only": True,
    "monitoring_recommends_review_only": True,
    "deterministic_only": True,
    "no_llm_required": True,
}

LANGSMITH_TRACES: tuple[str, ...] = (
    "catalyst_generation",
    "trigger_monitoring",
    "trigger_evaluation",
    "scenario_update",
)

NO_REDESIGN: tuple[str, ...] = (
    "judgment_stack",
    "investment_thesis_auto_rewrite",
    "price_targets",
    "buy_sell_orders",
)
