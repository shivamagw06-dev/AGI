"""P5 Investment Operations Layer — orchestration schema (not an intelligence engine)."""

from __future__ import annotations

ENGINE_CODE = "investment_operations"
ENGINE_NAME = "Investment Operations Layer"
VERSION = "p5-investment-operations-v1.0.0"
PROGRAMME = "AGIB_PHASE5_INVESTMENT_OPERATIONS_LAYER"
WORKSTREAM_ID = "P5"
MILESTONE = "phase_5_iol"

RECOMMENDATION_POLICY = "operations_orchestration_only_no_buy_sell"

CAPABILITIES = (
    "morning_office",
    "research_queue",
    "portfolio_operations",
    "monitoring_office",
    "decision_replay",
    "daily_brief",
    "catalyst_calendar",
    "alert_centre",
    "workspace",
    "operational_metrics",
)

BRIEF_TYPES = ("morning", "midday", "closing", "weekend", "monthly")

ALERT_TYPES = (
    "opportunity_score_change",
    "knowledge_delta",
    "contradiction",
    "catalyst",
    "portfolio_exposure",
    "hypothesis",
    "scenario",
    "macro_propagation",
    "monitoring",
)

PRIORITY_ORDER = ("Critical", "High", "Medium", "Low", "Monitor")
