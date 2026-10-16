"""AGI v4.0 Phase 5 Sprint 5.4 — Institutional Monitoring Office (IMO)."""

from __future__ import annotations

from typing import Any

IMO_VERSION = "institutional-monitoring-office-v1.0.0"
EVENT_SCHEMA_VERSION = "imo-event-schema-v1.0.0"
PROGRAMME = (
    "AGI v4.0 – Phase 5 Institutional Investment Office · Sprint 5.4 "
    "Institutional Monitoring Office"
)
MODULE_CODE = "IMO"
COMPANY = "AGI"
PRODUCT_LINE = "Institutional Investment Office"
OWNER = "AGI Investment Office"

FREEZE_LOCKS: dict[str, Any] = {
    "judgment_stack_v36": True,
    "investment_thesis": True,
    "decision_office": True,
    "portfolio_office": True,
    "events_do_not_mutate_thesis": True,
    "events_recommend_review_only": True,
    "no_orders": True,
    "no_positions": True,
    "no_execution": True,
    "soft_wire_only": True,
    "deterministic_only": True,
    "no_llm_monitoring_inflation": True,
}

# What CIO monitoring watches — not merely prices
MONITOR_DOMAINS: tuple[str, ...] = (
    "Earnings",
    "Guidance",
    "Management Commentary",
    "Corporate Actions",
    "Regulatory",
    "Macro",
    "Sector",
    "Competitor",
    "Valuation",
    "Confidence",
)

SEVERITIES: tuple[str, ...] = ("info", "low", "medium", "high", "critical")

RECOMMENDED_ACTIONS: tuple[str, ...] = (
    "Review",
    "Committee Review",
    "Escalate",
    "Refresh Thesis",
    "Monitor",
    "No Action",
)

TRIGGER_CODES: tuple[str, ...] = (
    "confidence_drop_gt_10",
    "bull_case_invalidated",
    "guidance_withdrawn",
    "quarterly_results_published",
    "valuation_shift",
    "sector_development",
    "competitor_event",
    "management_commentary",
    "corporate_action",
    "regulatory_change",
    "macro_indicator",
    "coverage_heartbeat",
)

EVENT_FIELDS: tuple[str, ...] = (
    "event_id",
    "portfolio_idea",
    "trigger",
    "source",
    "severity",
    "affected_thesis",
    "affected_decision",
    "affected_confidence",
    "recommended_action",
    "requires_review",
    "timestamp",
)

# Confidence drop threshold (percentage points) → Review
CONFIDENCE_DROP_REVIEW_THRESHOLD = 10.0
