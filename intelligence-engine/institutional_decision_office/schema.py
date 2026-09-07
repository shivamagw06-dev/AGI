"""AGI v4.0 Phase 5 Sprint 5.2 — Institutional Decision Office (IDO)."""

from __future__ import annotations

from typing import Any

IDO_VERSION = "institutional-decision-office-v1.0.0"
DECISION_SCHEMA_VERSION = "ido-decision-schema-v1.0.0"
PROGRAMME = (
    "AGI v4.0 – Phase 5 Institutional Investment Office · Sprint 5.2 "
    "Institutional Decision Office"
)
MODULE_CODE = "IDO"
COMPANY = "AGI"
PRODUCT_LINE = "Institutional Investment Office"
OWNER = "AGI Investment Office"

FREEZE_LOCKS: dict[str, Any] = {
    "judgment_stack_v36": True,
    "investment_thesis": True,  # consume ITE; do not redesign
    "evidence_weighting": True,
    "hypothesis_generation": True,
    "hypothesis_evaluation": True,
    "committee_reasoning": True,
    "confidence_calibration": True,
    "reasoning_frozen": True,
    "no_orders": True,
    "no_execution": True,
    "analysis_separate_from_decision": True,
    "soft_wire_only": True,
    "deterministic_only": True,
    "no_llm_decision_inflation": True,
}

# Institutional decisions — most are NOT buy/sell
DECISION_TYPES: tuple[str, ...] = (
    "Wait",
    "Monitor",
    "Increase Research",
    "Reject",
    "Escalate",
    "Approve",
    "Review After Earnings",
    "Review After Budget",
    "Review After Results",
)

# Explicitly not emitted by IDO v1
FORBIDDEN_DECISIONS: tuple[str, ...] = (
    "BUY",
    "SELL",
    "Buy",
    "Sell",
    "LONG",
    "SHORT",
    "EXECUTE",
    "ORDER",
)

# Decision lifecycle (CIO process)
DECISION_LIFECYCLE: tuple[str, ...] = (
    "Watch",
    "Research",
    "Committee Review",
    "Approved",
    "Monitoring",
    "Closed",
)

DECISION_OBJECT_FIELDS: tuple[str, ...] = (
    "decision_id",
    "thesis_id",
    "decision",
    "reason",
    "required_conditions",
    "dependencies",
    "confidence",
    "owner",
    "review_date",
    "review_trigger",
    "status",
    "version",
)
