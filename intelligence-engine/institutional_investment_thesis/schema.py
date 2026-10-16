"""AGI v4.0 / Phase 5 Sprint 5.1 — Institutional Investment Thesis Engine (ITE)."""

from __future__ import annotations

from typing import Any

ITE_VERSION = "institutional-investment-thesis-v1.0.0"
THESIS_SCHEMA_VERSION = "ite-thesis-schema-v1.0.0"
PROGRAMME = (
    "AGI v4.0 – Phase 5 Institutional Investment Office · Sprint 5.1 "
    "Institutional Investment Thesis Engine"
)
MODULE_CODE = "ITE"
COMPANY = "AGI"
PRODUCT_LINE = "Institutional Investment Office"
OWNER = "AGI Investment Office"

# Phase 4 judgment stack is frozen — ITE consumes only
FREEZE_LOCKS: dict[str, Any] = {
    "judgment_stack_v36": True,
    "evidence_weighting": True,
    "hypothesis_generation": True,
    "hypothesis_evaluation": True,
    "committee_reasoning": True,
    "confidence_calibration": True,
    "reasoning_frozen": True,
    "framework_selection": True,
    "communication": True,
    "no_buy_sell_in_ite": True,
    "analysis_not_decision": True,
    "soft_wire_only": True,
    "deterministic_only": True,
    "no_llm_thesis_inflation": True,
}

# Lifecycle — institutional investors think in lifecycles
LIFECYCLE_STATES: tuple[str, ...] = (
    "Draft",
    "Under Review",
    "Active",
    "Monitoring",
    "Needs Review",
    "Updated",
    "Closed",
    "Archived",
)

# Decision status for 5.1 — NOT buy/sell (IDE owns that in 5.2)
DECISION_STATUSES: tuple[str, ...] = (
    "Watch",
    "Under Review",
    "No Position",
    "Deferred",  # analysis may be positive; decision deferred
)

FORBIDDEN_DECISIONS: tuple[str, ...] = ("BUY", "SELL", "Buy", "Sell", "LONG", "SHORT")

# Ten institutional questions every thesis must answer
TEN_QUESTIONS: tuple[tuple[str, str], ...] = (
    ("investment_view", "What is the investment view?"),
    ("why_now", "Why now?"),
    ("what_market_missing", "What is the market missing?"),
    ("bull_case", "Bull case"),
    ("base_case", "Base case"),
    ("bear_case", "Bear case"),
    ("catalysts", "Key catalysts"),
    ("risks", "Key risks"),
    ("invalidation", "What invalidates this thesis?"),
    ("monitoring_checklist", "What should AGI monitor continuously?"),
)

DEFAULT_HOLDING_PERIOD = "12–36 months (default band until Decision Engine)"
