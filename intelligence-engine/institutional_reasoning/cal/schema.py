"""CAL schema — Continuous Adaptive Learning Phase 7 targets."""

from __future__ import annotations

from typing import Any

CAL_VERSION = "continuous-adaptive-learning-v1.0.0"
MODULE_CODE = "CAL"
PROGRAMME = "Continuous Adaptive Learning"

PROPOSAL_KINDS = (
    "increase_confidence",
    "decrease_confidence",
    "add_applicability_rule",
    "add_failure_condition",
    "adjust_planner_priority",
    "adjust_policy",
    "no_change",
)

PROPOSAL_STATUSES = (
    "proposed",
    "validated",
    "simulated",
    "approved",
    "rejected",
    "deployed",
)

PHASE7_TARGETS: dict[str, float] = {
    "learning_suite": 95.0,
    "traceability": 100.0,
    "ungoverned_changes": 0.0,
    "ies_regression": 0.0,
}

# Baseline planner weights (not production framework code — soft overlays).
BASE_PLANNER_WEIGHTS: dict[str, float] = {
    "rel_val_damodaran": 0.80,
    "hist_multiples": 0.75,
    "margin_of_safety": 0.70,
    "dcf_applicability": 0.65,
    "dcf_fcff": 0.60,
    "business_quality_roic": 0.78,
    "accounting_quality_screen": 0.72,
    "peer_comparison": 0.74,
}

BASE_POLICY: dict[str, float] = {
    "max_stock_weight": 0.08,
    "max_sector_weight": 0.25,
}
