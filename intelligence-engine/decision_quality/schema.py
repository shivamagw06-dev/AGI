"""Institutional Decision Quality schemas — observability only.

Measures decisions. Never reasons. Phases 1–7 and Knowledge Factory frozen.
"""

from __future__ import annotations

from typing import Any

IDQ_VERSION = "institutional-decision-quality-v1.0.0"
IDQ_SCHEMA_VERSION = "idq-schema-v1.0.0"

DECISION_METRICS: tuple[str, ...] = (
    "decision_accuracy",
    "evidence_completeness",
    "evidence_freshness",
    "evidence_quality",
    "framework_selection_accuracy",
    "framework_success_rate",
    "research_quality",
    "portfolio_quality",
    "risk_quality",
    "scenario_accuracy",
    "confidence_calibration",
    "timing_quality",
    "execution_quality",
    "outcome_accuracy",
    "learning_effectiveness",
)

FRAMEWORKS: tuple[str, ...] = (
    "damodaran_relative",
    "residual_income",
    "dcf",
    "margin_of_safety",
    "business_quality",
    "accounting_quality",
    "roic",
    "cash_flow",
    "ev_ebitda",
    "midcycle_dcf",
)

HALL_CATEGORIES: tuple[str, ...] = (
    "exceptional",
    "good",
    "average",
    "weak",
    "incorrect_missing_evidence",
    "incorrect_framework_selection",
    "incorrect_macro_assumption",
    "incorrect_portfolio_construction",
)

NORTH_STAR_COMPONENTS: tuple[str, ...] = (
    "decision_accuracy",
    "evidence_quality",
    "framework_accuracy",
    "confidence_calibration",
    "portfolio_quality",
    "research_quality",
    "outcome_quality",
)


def decision_envelope(decision_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "idq_schema_version": IDQ_SCHEMA_VERSION,
        "idq_version": IDQ_VERSION,
        "decision_id": decision_id,
        "observability_only": True,
        "never_reasons": True,
        "phases_1_7_untouched": True,
        "knowledge_factory_untouched": True,
        **payload,
    }
